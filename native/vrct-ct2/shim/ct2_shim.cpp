// C ABI over the ctranslate2.dll that ships in the Python ctranslate2 wheel, so Rust runs the very
// same binary (and its MKL / CUDA code paths) as the Python backend.
//
// Built with /MD against the CTranslate2 headers of the DLL's version (4.6.0): the C++ objects
// (std::string, std::vector, futures) cross the DLL boundary, so the CRT, the STL and the header
// version must all match the DLL. Each call mirrors what python/cpp/{translator,whisper}.cc and
// replica_pool.h do for the Python binding. Errors are returned as nullptr / -1 and the message
// is kept per thread (ct2_last_error).
#include <cstdio>
#include <cstring>
#include <exception>
#include <string>
#include <vector>

#include <ctranslate2/devices.h>
#include <ctranslate2/models/whisper.h>
#include <ctranslate2/translator.h>
#include <ctranslate2/types.h>
#include <ctranslate2/utils.h>

using namespace ctranslate2;

static thread_local std::string last_error;

template <typename F>
static auto guard(F&& f, decltype(f()) on_error) -> decltype(f()) {
  try {
    return f();
  } catch (const std::exception& e) {
    last_error = e.what();
  } catch (...) {
    last_error = "unknown C++ exception";
  }
  return on_error;
}

// '\0'-separated tokens -> vector<string>
static std::vector<std::string> split_tokens(const char* data, size_t count) {
  std::vector<std::string> tokens;
  tokens.reserve(count);
  for (size_t i = 0; i < count; ++i) {
    tokens.emplace_back(data);
    data += tokens.back().size() + 1;
  }
  return tokens;
}

template <typename Pool>
static Pool* new_pool(const char* model_path, const char* device, int device_index,
                      const char* compute_type, size_t inter_threads, size_t intra_threads) {
  // ReplicaPoolHelper in python/cpp/replica_pool.h
  models::ModelLoader loader(model_path);
  loader.device = str_to_device(device);
  loader.device_indices = {device_index};
  loader.compute_type = str_to_compute_type(compute_type);
  loader.num_replicas_per_device = inter_threads;
  ReplicaPoolConfig config;
  config.num_threads_per_replica = intra_threads;
  config.max_queued_batches = 0;
  return new Pool(loader, config);
}

extern "C" {

const char* ct2_last_error() { return last_error.c_str(); }

// Points the C runtime's stderr (shared by the DLLs built with the same UCRT, ctranslate2.dll
// included) at a file, so nothing reaches the UI's stderr pipe. Returns false on failure.
bool ct2_redirect_stderr(const char* path) {
  return std::freopen(path, "a", stderr) != nullptr;
}

int ct2_cuda_device_count() {
  return guard([] { return get_gpu_count(); }, 0);
}

// Bit set of supported compute types, as get_supported_compute_types in python/cpp/module.cc:
// 1 bfloat16, 2 float16, 4 int16, 8 int8.
int ct2_supported_compute_types(const char* device, int device_index) {
  return guard([&] {
    const auto d = str_to_device(device);
    return (mayiuse_bfloat16(d, device_index) ? 1 : 0) | (mayiuse_float16(d, device_index) ? 2 : 0)
         | (mayiuse_int16(d, device_index) ? 4 : 0) | (mayiuse_int8(d, device_index) ? 8 : 0);
  }, -1);
}

// ---- Translator -------------------------------------------------------------------------------

void* ct2_translator_new(const char* model_path, const char* device, int device_index,
                         const char* compute_type, size_t inter_threads, size_t intra_threads) {
  return guard([&]() -> void* {
    return new_pool<Translator>(model_path, device, device_index, compute_type, inter_threads, intra_threads);
  }, nullptr);
}

void ct2_translator_free(void* translator) { delete static_cast<Translator*>(translator); }

struct ct2_translate_options {
  size_t beam_size;
  size_t num_hypotheses;
  float length_penalty;
  float repetition_penalty;
  size_t no_repeat_ngram_size;
  size_t max_input_length;
  size_t max_decoding_length;
  bool return_scores;
};

void ct2_translate_options_default(ct2_translate_options* o) {
  TranslationOptions d;
  o->beam_size = d.beam_size;
  o->num_hypotheses = d.num_hypotheses;
  o->length_penalty = d.length_penalty;
  o->repetition_penalty = d.repetition_penalty;
  o->no_repeat_ngram_size = d.no_repeat_ngram_size;
  o->max_input_length = d.max_input_length;
  o->max_decoding_length = d.max_decoding_length;
  o->return_scores = d.return_scores;
}

// One source sentence (and its target prefix); the result is read with ct2_translation_*.
void* ct2_translate(void* translator, const char* source, size_t source_len, const char* prefix,
                    size_t prefix_len, const ct2_translate_options* o) {
  return guard([&]() -> void* {
    TranslationOptions options;
    options.beam_size = o->beam_size;
    options.num_hypotheses = o->num_hypotheses;
    options.length_penalty = o->length_penalty;
    options.repetition_penalty = o->repetition_penalty;
    options.no_repeat_ngram_size = o->no_repeat_ngram_size;
    options.max_input_length = o->max_input_length;
    options.max_decoding_length = o->max_decoding_length;
    options.return_scores = o->return_scores;
    auto* pool = static_cast<Translator*>(translator);
    // translate_batch_async + wait, as TranslatorWrapper::translate_batch does
    auto futures = pool->translate_batch_async({split_tokens(source, source_len)},
                                               {split_tokens(prefix, prefix_len)}, options);
    return new TranslationResult(futures[0].get());
  }, nullptr);
}

size_t ct2_translation_num_hypotheses(const void* r) {
  return static_cast<const TranslationResult*>(r)->hypotheses.size();
}
size_t ct2_translation_hypothesis_len(const void* r, size_t i) {
  return static_cast<const TranslationResult*>(r)->hypotheses[i].size();
}
const char* ct2_translation_token(const void* r, size_t i, size_t j) {
  return static_cast<const TranslationResult*>(r)->hypotheses[i][j].c_str();
}
float ct2_translation_score(const void* r, size_t i) {
  const auto* result = static_cast<const TranslationResult*>(r);
  return i < result->scores.size() ? result->scores[i] : 0.f;
}
void ct2_translation_free(void* r) { delete static_cast<TranslationResult*>(r); }

// ---- Whisper ----------------------------------------------------------------------------------

void* ct2_whisper_new(const char* model_path, const char* device, int device_index,
                      const char* compute_type, size_t inter_threads, size_t intra_threads) {
  return guard([&]() -> void* {
    return new_pool<models::Whisper>(model_path, device, device_index, compute_type, inter_threads, intra_threads);
  }, nullptr);
}

void ct2_whisper_free(void* whisper) { delete static_cast<models::Whisper*>(whisper); }

bool ct2_whisper_is_multilingual(const void* whisper) {
  return static_cast<const models::Whisper*>(whisper)->is_multilingual();
}
size_t ct2_whisper_n_mels(const void* whisper) { return static_cast<const models::Whisper*>(whisper)->n_mels(); }

// features: float32 [batch, n_mels, frames] on the CPU (StorageView.from_array). Returns the
// encoder output, to be freed with ct2_storage_free.
void* ct2_whisper_encode(void* whisper, float* features, size_t batch, size_t n_mels, size_t frames,
                         bool to_cpu) {
  return guard([&]() -> void* {
    StorageView view({static_cast<dim_t>(batch), static_cast<dim_t>(n_mels), static_cast<dim_t>(frames)},
                     features, Device::CPU);
    return new StorageView(static_cast<models::Whisper*>(whisper)->encode(view, to_cpu).get());
  }, nullptr);
}

void ct2_storage_free(void* storage) { delete static_cast<StorageView*>(storage); }

using LanguageProbs = std::vector<std::pair<std::string, float>>;

// Language probabilities of the first batch item, sorted by probability.
void* ct2_whisper_detect_language(void* whisper, const void* encoded) {
  return guard([&]() -> void* {
    auto futures = static_cast<models::Whisper*>(whisper)->detect_language(*static_cast<const StorageView*>(encoded));
    return new LanguageProbs(futures[0].get());
  }, nullptr);
}
size_t ct2_languages_len(const void* l) { return static_cast<const LanguageProbs*>(l)->size(); }
const char* ct2_languages_token(const void* l, size_t i) { return (*static_cast<const LanguageProbs*>(l))[i].first.c_str(); }
float ct2_languages_prob(const void* l, size_t i) { return (*static_cast<const LanguageProbs*>(l))[i].second; }
void ct2_languages_free(void* l) { delete static_cast<LanguageProbs*>(l); }

struct ct2_whisper_options {
  size_t beam_size;
  float patience;
  float length_penalty;
  float repetition_penalty;
  size_t no_repeat_ngram_size;
  size_t max_length;
  size_t sampling_topk;
  float sampling_temperature;
  size_t num_hypotheses;
  bool return_scores;
  bool return_no_speech_prob;
  size_t max_initial_timestamp_index;
  bool suppress_blank;
  const int* suppress_tokens;
  size_t suppress_tokens_len;
};

void ct2_whisper_options_default(ct2_whisper_options* o) {
  models::WhisperOptions d;
  o->beam_size = d.beam_size;
  o->patience = d.patience;
  o->length_penalty = d.length_penalty;
  o->repetition_penalty = d.repetition_penalty;
  o->no_repeat_ngram_size = d.no_repeat_ngram_size;
  o->max_length = d.max_length;
  o->sampling_topk = d.sampling_topk;
  o->sampling_temperature = d.sampling_temperature;
  o->num_hypotheses = d.num_hypotheses;
  o->return_scores = d.return_scores;
  o->return_no_speech_prob = d.return_no_speech_prob;
  o->max_initial_timestamp_index = d.max_initial_timestamp_index;
  o->suppress_blank = d.suppress_blank;
  o->suppress_tokens = nullptr;  // nullptr keeps the default {-1}
  o->suppress_tokens_len = 0;
}

// One prompt (token ids) for the first batch item; read with ct2_generation_*.
void* ct2_whisper_generate(void* whisper, const void* encoded, const size_t* prompt, size_t prompt_len,
                           const ct2_whisper_options* o) {
  return guard([&]() -> void* {
    models::WhisperOptions options;
    options.beam_size = o->beam_size;
    options.patience = o->patience;
    options.length_penalty = o->length_penalty;
    options.repetition_penalty = o->repetition_penalty;
    options.no_repeat_ngram_size = o->no_repeat_ngram_size;
    options.max_length = o->max_length;
    options.sampling_topk = o->sampling_topk;
    options.sampling_temperature = o->sampling_temperature;
    options.num_hypotheses = o->num_hypotheses;
    options.return_scores = o->return_scores;
    options.return_no_speech_prob = o->return_no_speech_prob;
    options.max_initial_timestamp_index = o->max_initial_timestamp_index;
    options.suppress_blank = o->suppress_blank;
    if (o->suppress_tokens)
      options.suppress_tokens.assign(o->suppress_tokens, o->suppress_tokens + o->suppress_tokens_len);
    std::vector<std::vector<size_t>> prompts{std::vector<size_t>(prompt, prompt + prompt_len)};
    auto futures = static_cast<models::Whisper*>(whisper)->generate(*static_cast<const StorageView*>(encoded),
                                                                   std::move(prompts), options);
    return new models::WhisperGenerationResult(futures[0].get());
  }, nullptr);
}

size_t ct2_generation_num_sequences(const void* r) {
  return static_cast<const models::WhisperGenerationResult*>(r)->sequences_ids.size();
}
size_t ct2_generation_sequence_len(const void* r, size_t i) {
  return static_cast<const models::WhisperGenerationResult*>(r)->sequences_ids[i].size();
}
const size_t* ct2_generation_sequence(const void* r, size_t i) {
  return static_cast<const models::WhisperGenerationResult*>(r)->sequences_ids[i].data();
}
float ct2_generation_score(const void* r, size_t i) {
  const auto* result = static_cast<const models::WhisperGenerationResult*>(r);
  return i < result->scores.size() ? result->scores[i] : 0.f;
}
float ct2_generation_no_speech_prob(const void* r) {
  return static_cast<const models::WhisperGenerationResult*>(r)->no_speech_prob;
}
void ct2_generation_free(void* r) { delete static_cast<models::WhisperGenerationResult*>(r); }

}  // extern "C"

// Check-only C ABI, adapted from ../vrct-ct2/shim/ct2_shim.cpp.
// Compile ONLY with the supplied CTranslate2 v4.9.0 headers and matching release
// MSVC/STL (/MD, _ITERATOR_DEBUG_LEVEL=0) DLL. All C++ allocation stays here.
#include <algorithm>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#include <ctranslate2/devices.h>
#include <ctranslate2/models/whisper.h>
#include <ctranslate2/translator.h>
#include <ctranslate2/types.h>
#include <ctranslate2/utils.h>

using namespace ctranslate2;
#define API extern "C" __declspec(dllexport)
static thread_local std::string last_error;

template <typename F, typename T>
static T guard(F&& f, T failure) {
  try {
    last_error.clear();
    return f();
  } catch (const std::exception& e) {
    last_error = e.what();
  } catch (...) {
    last_error = "unknown C++ exception";
  }
  return failure;
}

struct Model {
  std::unique_ptr<models::Whisper> whisper;
  std::unique_ptr<Translator> translator;
};

API const char* ct2_49_error() { return last_error.c_str(); }
API int ct2_49_protocol() { return 2; }
API int ct2_49_gpu_count() {
  return guard([] { return static_cast<int>(get_gpu_count()); }, -1);
}
// Same capability primitives used by CT2's Python get_supported_compute_types.
API int ct2_49_compute_types(const char* device) {
  return guard([&] {
    const auto d = str_to_device(device);
    return (mayiuse_bfloat16(d, 0) ? 1 : 0) | (mayiuse_float16(d, 0) ? 2 : 0)
         | (mayiuse_int16(d, 0) ? 4 : 0) | (mayiuse_int8(d, 0) ? 8 : 0);
  }, -1);
}

API void* ct2_49_model_new(const char* path, const char* device, const char* compute, int whisper) {
  return guard([&]() -> void* {
    models::ModelLoader loader(path);
    loader.device = str_to_device(device);
    loader.device_indices = {0};
    loader.compute_type = str_to_compute_type(compute);
    loader.num_replicas_per_device = 1;  // both callers share one pool AND one replica
    ReplicaPoolConfig config;
    config.num_threads_per_replica = 4;
    config.max_queued_batches = 0;
    auto model = std::make_unique<Model>();
    if (whisper)
      model->whisper = std::make_unique<models::Whisper>(loader, config);
    else
      model->translator = std::make_unique<Translator>(loader, config);
    return model.release();
  }, static_cast<void*>(nullptr));
}
API int ct2_49_model_free(void* model) {
  return guard([&] { delete static_cast<Model*>(model); return 0; }, -1);
}
API int ct2_49_model_info(void* handle, char* output, size_t capacity) {
  return guard([&] {
    auto& model = *static_cast<Model*>(handle);
    const auto& m = model.whisper ? model.whisper->get_first_replica().model()
                                 : model.translator->get_first_replica().model();
    const std::string text = "{\"effective_compute_type\":\"" + compute_type_to_str(m->effective_compute_type())
      + "\",\"saved_compute_type\":\"" + compute_type_to_str(m->saved_compute_type())
      + "\",\"device\":\"" + device_to_str(m->device()) + "\"}";
    if (text.size() + 1 > capacity) throw std::runtime_error("model info buffer too small");
    std::memcpy(output, text.c_str(), text.size() + 1);
    return static_cast<int>(text.size());
  }, -1);
}
API int ct2_49_whisper_mels(void* model) {
  return guard([&] { return static_cast<int>(static_cast<Model*>(model)->whisper->n_mels()); }, -1);
}
API int ct2_49_whisper_multilingual(void* model) {
  return guard([&] { return static_cast<Model*>(model)->whisper->is_multilingual() ? 1 : 0; }, -1);
}

// Private features and encoder output per call; only the thread-safe replica pool is shared.
API int ct2_49_transcribe(void* model, float* features, size_t mels, size_t frames,
                         const size_t* prompt, size_t prompt_len,
                         size_t* output, size_t capacity) {
  return guard([&] {
    auto& whisper = *static_cast<Model*>(model)->whisper;
    StorageView view({1, static_cast<dim_t>(mels), static_cast<dim_t>(frames)}, features, Device::CPU);
    auto encoded = whisper.encode(view, false).get();
    models::WhisperOptions options;
    options.beam_size = 1;
    // v4.9.0 whisper.cc は min(max_length/2, max_length-start_step) を使用。
    // 固定した短い SOT/en/transcribe/no_timestamps prompt で生成上限を128にする。
    options.max_length = 256;
    options.sampling_topk = 1;
    options.sampling_temperature = 0;
    options.num_hypotheses = 1;
    std::vector<std::vector<size_t>> prompts{std::vector<size_t>(prompt, prompt + prompt_len)};
    auto futures = whisper.generate(encoded, std::move(prompts), options);
    auto result = futures.at(0).get();
    const auto& ids = result.sequences_ids.at(0);
    if (ids.size() >= 128)
      throw std::runtime_error("Whisper reached the diagnostic token limit; inspect output/inputs");
    if (ids.size() > capacity)
      throw std::runtime_error("Whisper result exceeds C ABI buffer");
    std::copy(ids.begin(), ids.end(), output);
    return static_cast<int>(ids.size());
  }, -1);
}

// NUL-separated UTF-8 tokens in/out. No STL objects or owning pointers cross the C ABI.
API int ct2_49_translate(void* model, const char* source, size_t count,
                        char* output, size_t capacity) {
  return guard([&] {
    std::vector<std::string> tokens;
    tokens.reserve(count);
    for (size_t i = 0; i < count; ++i) {
      tokens.emplace_back(source);
      source += tokens.back().size() + 1;
    }
    TranslationOptions options;
    options.beam_size = 2;  // app / CT2 default
    options.max_decoding_length = 128;
    auto futures = static_cast<Model*>(model)->translator->translate_batch_async(
        {tokens}, {{"jpn_Jpan"}}, options);
    auto result = futures.at(0).get();
    const auto& hypothesis = result.hypotheses.at(0);
    if (hypothesis.size() >= options.max_decoding_length)
      throw std::runtime_error("NLLB reached the diagnostic token limit; inspect output/inputs");
    size_t written = 0;
    for (const auto& token : hypothesis) {
      if (token.size() + 1 > capacity - written)
        throw std::runtime_error("NLLB result exceeds C ABI buffer");
      std::memcpy(output + written, token.c_str(), token.size() + 1);
      written += token.size() + 1;
    }
    return static_cast<int>(written);
  }, -1);
}

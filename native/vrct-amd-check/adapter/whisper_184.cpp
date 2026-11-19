// 検証専用。v1.8.4 のヘッダーと Vulkan 配布 DLL に対してのみビルドする。
#include <whisper.h>
#include "token_budget.h"
#include "mel_input.h"
#include <cstdio>
#include <cstring>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>

#define API extern "C" __declspec(dllexport)
static thread_local std::string last_error;

template <typename F, typename T> static T guard(F&& f, T failure) {
  try { last_error.clear(); return f(); }
  catch (const std::exception& e) { last_error = e.what(); }
  catch (...) { last_error = "unknown whisper.cpp exception"; }
  return failure;
}

struct Model {
  whisper_context* context = nullptr;
  whisper_full_params params;
  std::string expected_backend;
  bool backend_verified = false;
  bool prepared = false;
  int max_decode_steps;
  explicit Model(bool gpu, int device, int threads, int max_tokens)
      : params(whisper_full_default_params(WHISPER_SAMPLING_GREEDY)),
        expected_backend("using Vulkan" + std::to_string(device) + " backend"),
        max_decode_steps(max_tokens) {
    params.n_threads = threads;
    params.language = "en";
    params.detect_language = false;
    params.translate = false;
    params.no_context = true;
    params.no_timestamps = true;
    params.single_segment = true;
    params.print_progress = false;
    params.print_realtime = false;
    params.print_timestamps = false;
    params.print_special = false;
    params.token_timestamps = false;
    params.vad = false;
    params.initial_prompt = nullptr;
    params.prompt_tokens = nullptr;
    params.prompt_n_tokens = 0;
    params.max_tokens = last_decode_step(max_tokens);
    params.greedy.best_of = 1;
    params.temperature = 0;
    params.temperature_inc = 0;
    params.suppress_blank = true;
    params.suppress_nst = true;
    params.entropy_thold = std::numeric_limits<float>::infinity();
    params.logprob_thold = -std::numeric_limits<float>::infinity();
    params.no_speech_thold = 1.0f;
    backend_verified = !gpu;
  }
  ~Model() {
    if (context) whisper_free(context);
    whisper_log_set(nullptr, nullptr);
  }
};

static void log_callback(enum ggml_log_level, const char* text, void* user) {
  auto* model = static_cast<Model*>(user);
  if (text && std::strstr(text, model->expected_backend.c_str()))
    model->backend_verified = true;
  if (text) std::fputs(text, stderr);
}

API int whisper_184_protocol() { return 2; }
API const char* whisper_184_error() { return last_error.c_str(); }
API const char* whisper_184_version() { return whisper_version(); }
API void* whisper_184_model_new(const char* path, int gpu, int device, int threads, int max_tokens) {
  return guard([&]() -> void* {
    auto model = std::make_unique<Model>(gpu != 0, device, threads, max_tokens);
    whisper_log_set(log_callback, model.get());
    auto params = whisper_context_default_params();
    params.use_gpu = gpu != 0;
    params.gpu_device = device;
    // CT2 の HIP ビルドにない Flash Attention を比較に混ぜない。
    params.flash_attn = false;
    model->context = whisper_init_from_file_with_params(path, params);
    if (!model->context) throw std::runtime_error("whisper model load failed");
    if (!model->backend_verified)
      throw std::runtime_error("requested Vulkan backend was not used (CPU fallback rejected)");
    return model.release();
  }, static_cast<void*>(nullptr));
}
API int whisper_184_model_free(void* handle) {
  return guard([&] { delete static_cast<Model*>(handle); return 0; }, -1);
}
API int whisper_184_prepare(void* handle, const float* values, size_t count,
                            int mels, int frames, int original_samples) {
  return guard([&] {
    auto& model = *static_cast<Model*>(handle);
    // 失敗時に前回のmelを再利用しない。
    model.prepared = false;
    if (!valid_common_mel(values, count, mels, frames, original_samples))
      throw std::runtime_error("common mel requires finite 128x3000 float32 and 3200..480000 original samples");
    if (whisper_model_n_mels(model.context) != mels || whisper_model_n_audio_ctx(model.context) * 2 != frames)
      throw std::runtime_error("model does not match the common 128x3000 mel geometry");
    if (whisper_set_mel(model.context, values, frames, mels) != 0)
      throw std::runtime_error("whisper common mel copy failed");
    // set_melはn_len_orgも3000にするため、元の音声長を別に保存する。
    // ミリ秒未満は切り捨て。full内部の10ms単位丸めはencoder入力を変更しない。
    model.params.offset_ms = 0;
    model.params.audio_ctx = 0;
    model.params.duration_ms = common_mel_duration_ms(original_samples);
    model.prepared = true;
    return 0;
  }, -1);
}
API int whisper_184_transcribe(void* handle, char* output, size_t capacity) {
  return guard([&] {
    auto& model = *static_cast<Model*>(handle);
    if (!model.prepared) throw std::runtime_error("mel must be prepared before inference");
    // v1.8.4 は samples==nullptr,n_samples==0 なら既存 mel を使用する。
    // 同じ context を warmup と全測定で再利用する。並行呼び出しは禁止。
    if (whisper_full(model.context, model.params, nullptr, 0) != 0)
      throw std::runtime_error("whisper inference failed");
    std::string text;
    int tokens = 0;
    bool ends_with_eot = false;
    for (int i = 0; i < whisper_full_n_segments(model.context); ++i) {
      text += whisper_full_get_segment_text(model.context, i);
      const int count = whisper_full_n_tokens(model.context, i);
      tokens += count;
      if (count > 0)
        ends_with_eot = whisper_full_get_token_id(model.context, i, count - 1) == whisper_token_eot(model.context);
    }
    if (!completed_within_budget(tokens, ends_with_eot, model.max_decode_steps))
      throw std::runtime_error("Whisper did not finish with EOT within the comparison token budget");
    if (text.empty() || text.size() + 1 > capacity)
      throw std::runtime_error("empty or oversized whisper transcript");
    std::memcpy(output, text.c_str(), text.size() + 1);
    return static_cast<int>(text.size());
  }, -1);
}

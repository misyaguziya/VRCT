//! Silero VAD v5 as audio_vad.SileroFrameProbability runs faster-whisper's model
//! (silero_encoder_v5.onnx / silero_decoder_v5.onnx): 64 samples of context and a 512-sample
//! frame go to the encoder, its (1, 128) output and the (2, 1, 128) state to the decoder.
use crate::R;
use ort::{ep, session::Session, value::Tensor};
use std::path::Path;

pub struct SileroVad {
    encoder: Session,
    decoder: Session,
    state: Vec<f32>,
    context: Vec<f32>,
}

/// One thread and no memory arena, as faster-whisper's SileroVADModel opens them
fn session(path: &Path) -> R<Session> {
    crate::init_ort()?;
    fn open(path: &Path) -> ort::Result<Session> {
        Session::builder()?
            .with_inter_threads(1)?
            .with_intra_threads(1)?
            .with_execution_providers([ep::CPU::default().with_arena_allocator(false).build()])?
            .commit_from_file(path)
    }
    Ok(open(path)?)
}

impl SileroVad {
    /// `assets`: the folder with silero_encoder_v5.onnx and silero_decoder_v5.onnx
    pub fn new(assets: &Path) -> R<Self> {
        Ok(Self {
            encoder: session(&assets.join("silero_encoder_v5.onnx"))?,
            decoder: session(&assets.join("silero_decoder_v5.onnx"))?,
            state: vec![0.0; 2 * 128],
            context: vec![0.0; 64],
        })
    }

    pub fn reset(&mut self) {
        self.state.fill(0.0);
        self.context.fill(0.0);
    }

    /// The speech probability of a 512-sample frame (16 kHz, -1..1)
    pub fn probability(&mut self, frame: &[f32]) -> R<f32> {
        if frame.len() != 512 {
            return Err(format!("expected a 512-sample frame, got {}", frame.len()).into());
        }
        let mut input = Vec::with_capacity(576);
        input.extend_from_slice(&self.context);
        input.extend_from_slice(frame);
        let out = self.encoder.run(ort::inputs!["input" => Tensor::from_array(([1usize, 576], input))?])?;
        let encoded = out[0].try_extract_tensor::<f32>()?.1.to_vec();
        drop(out);
        let out = self.decoder.run(ort::inputs![
            "input" => Tensor::from_array(([1usize, 128], encoded))?,
            "state" => Tensor::from_array(([2usize, 1, 128], self.state.clone()))?,
        ])?;
        let probability = out[0].try_extract_tensor::<f32>()?.1[0];
        self.state = out[1].try_extract_tensor::<f32>()?.1.to_vec();
        self.context.copy_from_slice(&frame[448..]);
        Ok(probability)
    }
}

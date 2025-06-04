const EventEmitter = require("events");
const { Buffer } = require("node:buffer");
const fetch = require("node-fetch");

class TextToSpeechService extends EventEmitter {
  constructor(config) {
    super();
    this.config = config;
    this.config.voiceId ||= process.env.VOICE_ID;
    this.nextExpectedIndex = 0;
    this.speechBuffer = {};
  }

  async generate(gptReply, interactionCount, language) {
    const { partialResponseIndex, partialResponse } = gptReply;
    console.log("Fetched language from there is :", language)
    if (!partialResponse) {
      return;
    }
    if(language=="es"){
      this.config.voiceId="br0MPoLVxuslVxf61qHn" //"PrwKJdvtTbJVdosRhS1O";
      console.log("Spanish Voice Id Setup..")
    }

    try {
      const outputFormat = "ulaw_8000";
      console.time("Speech generation time : ".green)
      const response = await fetch(
        `https://api.elevenlabs.io/v1/text-to-speech/${this.config.voiceId}/stream?output_format=${outputFormat}&optimize_streaming_latency=2`,
        {
          method: "POST",
          headers: {
            "xi-api-key": process.env.XI_API_KEY,
            "Content-Type": "application/json",
            accept: "audio/wav",
          },
          // TODO: Pull more config? https://docs.elevenlabs.io/api-reference/text-to-speech-stream
          body: JSON.stringify({
            model_id: process.env.XI_MODEL_ID,
            text: partialResponse,
            voice_settings: {
              stability: 0.35,
              similarity_boost: 0.3,
              style: 0.2
          },
          }),
        },
      );
      const audioArrayBuffer = await response.arrayBuffer();
      console.timeEnd("Speech generation time : ".green)
      this.emit(
        "speech",
        partialResponseIndex,
        Buffer.from(audioArrayBuffer).toString("base64"),
        partialResponse,
        interactionCount,
      );
    } catch (err) {
      console.error("Error occurred in TextToSpeech service");
      console.error(err);
    }
  }
}

module.exports = { TextToSpeechService };

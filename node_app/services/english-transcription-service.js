require("colors");
const { Deepgram } = require("@deepgram/sdk");
const { Buffer } = require("node:buffer");
const { GptService } = require("./gpt-service");
const EventEmitter = require("events");


const gptService = new GptService();
class EnglishTranscriptionService extends EventEmitter {
  sid;
  constructor() {
    super();
    const deepgram = new Deepgram(process.env.DEEPGRAM_API_KEY);
    this.deepgramLive = deepgram.transcription.live({
      encoding: "mulaw",
      sample_rate: "8000",
      model: "nova-3",
      punctuate: true,
      interim_results: true,
      endpointing: 200,
      utterance_end_ms: 1100,
      language: "en-US",
      // detected_language: true,
    });

    this.finalResult = "";
    this.speechFinal = false; // used to determine if we have seen speech_final=true indicating that deepgram detected a natural pause in the speakers speech.
    let language = ""; 
    this.deepgramLive.addListener(
      "transcriptReceived",
      (transcriptionMessage) => {
        const transcription = JSON.parse(transcriptionMessage);
        const alternatives = transcription.channel?.alternatives;
        // console.log(alternatives[0]?.languages)
        const detected_language = transcription.channel?.detected_language;
        let text = "";
        
        // console.log("%%%%%% Alternatives %%%%%%\n", alternatives[0])
        if (alternatives) {
          text = alternatives[0]?.transcript;
          
        }
        // if (alternatives && alternatives.length > 0) {
        //   const words = alternatives[0]?.words;
          
        //   if (words && words.length > 0) {
        //     // Count frequency of each language in words array
        //     console.log("+=+ Words length +=+", words.length)
        //     const languageFrequency = {};
        //     words.forEach(word => {
        //       console.log("+=+ Word  +=+", word)
        //       if (word.language) {
        //         languageFrequency[word.language] = (languageFrequency[word.language] || 0) + 1;
        //       }
        //     });

        //     // Find the language with highest frequency
        //     let maxFreq = 0;
        //     let mostFrequentLang = '';
        //     Object.entries(languageFrequency).forEach(([lang, freq]) => {
        //       if (freq > maxFreq) {
        //         maxFreq = freq;
        //         mostFrequentLang = lang;
        //       }
        //     });

        //     if (mostFrequentLang) {
        //       language = mostFrequentLang;
        //     }
        //   }
        //   console.log("+=+ Language  +=+", language)
        // } 
        // console.log("+=+ Detected Language  +=+", language)

        
        // if we receive an UtteranceEnd and speech_final has not already happened then we should consider this the end of of the human speech and emit the transcription
        if (transcription.type === "UtteranceEnd") {
          if (!this.speechFinal) {
            console.log(
              `UtteranceEnd received before speechFinal, emit the text collected so far: ${this.finalResult}`
                .yellow,
            );
            this.emit("transcription", this.finalResult);
            // English service doesn't need to emit language events
            return;
          } else {
            console.log(
              "STT -> Speech was already final when UtteranceEnd recevied"
                .yellow,
            );
            return;
          }
        }
        // if is_final that means that this chunk of the transcription is accurate and we need to add it to the finalResult
        if (transcription.is_final === true && text.trim().length > 0) {
          this.finalResult += ` ${text}`;
          // if speech_final and is_final that means this text is accurate and it's a natural pause in the speakers speech. We need to send this to the assistant for processing
          if (transcription.speech_final === true) {
            this.speechFinal = true; // this will prevent a utterance end which shows up after speechFinal from sending another response
            this.emit("transcription", this.finalResult);
            // English service doesn't need to emit language events
            this.finalResult = "";
          } else {
            // if we receive a message without speechFinal reset speechFinal to false, this will allow any subsequent utteranceEnd messages to properly indicate the end of a message
            this.speechFinal = false;
          }
        } else {
          this.emit("utterance", text);
          // English service doesn't need to emit language events
        }
      },
    );

    this.deepgramLive.addListener("error", (error) => {
      console.error("STT -> deepgram error");
      console.error(error);
    });

    this.deepgramLive.addListener("warning", (warning) => {
      console.error("STT -> deepgram warning");
      console.error(warning);
    });

    this.deepgramLive.addListener("metadata", (metadata) => {
      console.error("STT -> deepgram metadata");
      console.error(metadata);
    });

    this.deepgramLive.addListener("close", () => {
      // console.log("&&&&&&&&&&&&&&&&&&&&&&&&&&",this)
      if (this.sid){
      console.log("Ending the Call... with SID", this.sid)
      fetch(`http://98.82.75.144:8000/call_end?call_sid=${this.sid}`, {method:"POST"}) 
      console.log("Calling Judge_sms_email");
      gptService.judge_sms_email(this.sid) 
      }// Neeed to fix this
    console.log("STT -> Deepgram English connection closed".yellow);
    });
  }

  /**
   * Send the payload to Deepgram
   * @param {String} payload A base64 MULAW/8000 audio stream
   */
  send(payload, callSid) {
    // TODO: Buffer up the media and then send
    // console.log(callSid)
    if(callSid==null || callSid==undefined){}
    else {
      
      this.sid = callSid;

    }
    if (this.deepgramLive.getReadyState() === 1) {
      this.deepgramLive.send(Buffer.from(payload, "base64"));
    }
  }

  closeDeepgram(){
    if(this.deepgramLive){
      // this.deepgramLive.close();
      this.deepgramLive.finish();
      console.log("Deepgram Live Listener Closed");
    }
  }
}

module.exports = { EnglishTranscriptionService };

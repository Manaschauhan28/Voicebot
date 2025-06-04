const EventEmitter = require("events");
const uuid = require("uuid");
const fs = require("fs");
const { WaveFile } = require("wavefile");
const ffmpeg = require("fluent-ffmpeg");


class StreamService extends EventEmitter {
	
	constructor(websocket) {
	console.log("In entering , Stream Service".yellow)
	// console.log(websocket)
	  super();
	  this.ws = websocket;
	  this.expectedAudioIndex = 0;
	  this.audioBuffer = {};
	  this.streamSid = "";
	}
	
	setStreamSid(streamSid) {
	console.log("Stream ID Setup done".red)
	  this.streamSid = streamSid;
	}
  
	buffer(index, audio) {
	  // Escape hatch for intro message, which doesn't have an index
	  console.log("SENDING AUDIO TO MOBILE")
	  if (index === null) {
		this.sendAudio(audio);
	  } else if (index === this.expectedAudioIndex) {
		this.sendAudio(audio);
		this.expectedAudioIndex++;
  
		while (
		  Object.prototype.hasOwnProperty.call(
			this.audioBuffer,
			this.expectedAudioIndex,
		  )
		) {
		  const bufferedAudio = this.audioBuffer[this.expectedAudioIndex];
		  this.sendAudio(bufferedAudio);
		  this.expectedAudioIndex++;
		}
	  } else {
		this.audioBuffer[index] = audio;
	  }
	}
  
	sendAudio(audio) {
	  console.log("I am in Send audio Function")
	  this.ws.send(
		JSON.stringify({
		  streamSid: this.streamSid,
		  event: "media",
		  // event:"playAudio",
		  media: {
			payload: audio,
		  },
		}),
	  );
	  // When the media completes you will receive a `mark` message with the label
	  const markLabel = uuid.v4();
	  this.ws.send(
		JSON.stringify({
		  streamSid: this.streamSid,
		  event: "mark",
		  mark: {
			name: markLabel,
		  },
		}),
	  );
	  this.emit("audiosent", markLabel);
	}
  
	async think(filePath) {
	  try {
		// Convert MP3 to WAV
  
		const wavFilePath = filePath.replace(".mp3", ".wav");
		// Check if WAV file already exists
		if (fs.existsSync(wavFilePath)) {
		  console.log("WAV file already exists.");
		} else {
		  // Convert MP3 to WAV
		  await this.convertMP3ToWAV(filePath, wavFilePath);
		}
		const wavData = fs.readFileSync(wavFilePath);
		let wav = new WaveFile(wavData);
		wav.toSampleRate(8000);
		wav.toMuLaw();
		// Read WAV file
		// Extract only the raw µ-law audio data, excluding headers
		const rawMuLawData = wav.data.samples;
  
		  let base64Chunk = Buffer.from(rawMuLawData).toString("base64");
		  this.sendAudio(base64Chunk);
		
  
		// Convert WAV to base64
  
		// Send the audio over WebSocket
  
		// Clean up temporary WAV file

	  } catch (err) {
		console.error(
		  "Error occurred while reading the audio file, converting, or sending over WebSocket",
		);
		console.error(err);
	  }
	}
  
	convertMP3ToWAV(mp3FilePath, wavFilePath) {
	  return new Promise((resolve, reject) => {
		ffmpeg(mp3FilePath)
		  .toFormat("wav")
		  .on("end", resolve)
		  .on("error", reject)
		  .save(wavFilePath);
	  });
	}
  }



  
module.exports = { StreamService };
  
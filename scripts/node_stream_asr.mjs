#!/usr/bin/env node

import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
import os from 'node:os';
import path from 'node:path';

function getArg(name, fallback = '') {
	const index = process.argv.indexOf(name);
	if (index === -1) {
		return fallback;
	}

	return process.argv[index + 1] ?? fallback;
}

function getModelPath(modelDir) {
	return modelDir || path.join(
		os.homedir(),
		'.coli',
		'models',
		'sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17',
	);
}

function getVadModelPath(vadModelPath) {
	return vadModelPath || path.join(os.homedir(), '.coli', 'models', 'silero_vad.onnx');
}

function getPunctuationModelPath(punctuationModelPath) {
	return punctuationModelPath;
}

function createSherpa(projectDir) {
	const require = createRequire(path.join(projectDir, 'package.json'));
	return require('sherpa-onnx-node');
}

function createRecognizer(sherpaOnnx, modelDir, numThreads) {
	return new sherpaOnnx.OfflineRecognizer({
		featConfig: {sampleRate: 16000, featureDim: 80},
		modelConfig: {
			senseVoice: {
				model: path.join(modelDir, 'model.int8.onnx'),
				useInverseTextNormalization: 1,
			},
			tokens: path.join(modelDir, 'tokens.txt'),
			numThreads,
			provider: 'cpu',
			debug: 0,
		},
	});
}

function createVad(sherpaOnnx, vadModelPath) {
	return new sherpaOnnx.Vad(
		{
			sileroVad: {
				model: vadModelPath,
				threshold: 0.5,
				minSpeechDuration: 0.25,
				minSilenceDuration: 0.5,
				maxSpeechDuration: 15,
				windowSize: 512,
			},
			sampleRate: 16000,
			debug: 0,
			numThreads: 1,
		},
		60,
	);
}

function createPunctuation(sherpaOnnx, punctuationModelPath, numThreads) {
	if (!punctuationModelPath) {
		return null;
	}

	return new sherpaOnnx.OfflinePunctuation({
		model: {
			ctTransformer: punctuationModelPath,
			numThreads,
			provider: 'cpu',
			debug: false,
		},
	});
}

function recognize(recognizer, samples) {
	const stream = recognizer.createStream();
	stream.acceptWaveform({sampleRate: 16000, samples});
	recognizer.decode(stream);
	return recognizer.getResult(stream);
}

async function* ffmpegPcmStream(inputPath) {
	const ffmpeg = spawn(
		'ffmpeg',
		[
			'-hide_banner',
			'-loglevel',
			'error',
			'-nostdin',
			'-i',
			inputPath,
			'-f',
			's16le',
			'-acodec',
			'pcm_s16le',
			'-ac',
			'1',
			'-ar',
			'16000',
			'pipe:1',
		],
		{stdio: ['ignore', 'pipe', 'pipe']},
	);

	let stderr = '';
	ffmpeg.stderr.on('data', (chunk) => {
		stderr += chunk.toString();
	});

	for await (const chunk of ffmpeg.stdout) {
		const buffer = Buffer.from(chunk);
		const pcm = new Int16Array(
			buffer.buffer,
			buffer.byteOffset,
			Math.floor(buffer.byteLength / 2),
		);
		const float32 = new Float32Array(pcm.length);
		for (let i = 0; i < pcm.length; i += 1) {
			float32[i] = pcm[i] / 32768;
		}

		yield float32;
	}

	const exitCode = await new Promise((resolve) => {
		ffmpeg.on('close', resolve);
	});
	if (exitCode !== 0) {
		throw new Error(`ffmpeg failed: ${stderr.trim() || exitCode}`);
	}
}

async function main() {
	const inputPath = getArg('--input');
	if (!inputPath) {
		throw new Error('--input is required');
	}

	const projectDir = getArg('--project-dir');
	if (!projectDir) {
		throw new Error('--project-dir is required');
	}

	const modelDir = getModelPath(getArg('--model-dir'));
	const vadModelPath = getVadModelPath(getArg('--vad-model'));
	const punctuationModelPath = getPunctuationModelPath(getArg('--punc-model'));
	const numThreads = Number.parseInt(getArg('--cores', '2'), 10) || 2;

	const sherpaOnnx = createSherpa(projectDir);
	const recognizer = createRecognizer(sherpaOnnx, modelDir, numThreads);
	const vad = createVad(sherpaOnnx, vadModelPath);
	const punctuation = createPunctuation(sherpaOnnx, punctuationModelPath, numThreads);
	const windowSize = vad.config.sileroVad.windowSize;

	const results = [];
	let pending = new Float32Array(0);

	function drainSegments() {
		while (!vad.isEmpty()) {
			const segment = vad.front(true);
			vad.pop();
			const result = recognize(recognizer, segment.samples);
			const rawText = result.text.trim();
			if (!rawText) {
				continue;
			}

			const text = punctuation ? punctuation.addPunct(rawText).trim() : rawText;

			const start = Number((segment.start / 16000).toFixed(3));
			const end = Number(
				((segment.start + segment.samples.length) / 16000).toFixed(3),
			);
			results.push({start, end, text, raw_text: rawText});
		}
	}

	for await (const chunk of ffmpegPcmStream(inputPath)) {
		const combined = new Float32Array(pending.length + chunk.length);
		combined.set(pending);
		combined.set(chunk, pending.length);
		pending = combined;

		while (pending.length >= windowSize) {
			vad.acceptWaveform(pending.subarray(0, windowSize));
			pending = pending.subarray(windowSize);
			drainSegments();
		}
	}

	if (pending.length > 0) {
		const padded = new Float32Array(windowSize);
		padded.set(pending);
		vad.acceptWaveform(padded);
	}

	vad.flush();
	drainSegments();

	process.stdout.write(JSON.stringify(results));
}

main().catch((error) => {
	process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
	process.exit(1);
});

const ivrFlow = import("./ivrFlow.json");

let speechUtterance;
function speak(text) {
    if (speechUtterance) {
        speechSynthesis.cancel();
    }
    speechUtterance = new SpeechSynthesisUtterance(text);
    speechSynthesis.speak(speechUtterance);
}

function startCall() {
    document.getElementById("callButton").style.display = "none";
    document.getElementById("ivrScreen").style.display = "block";
    document.getElementById("dialPad").style.display = "grid";
    updateIVR("welcome");
}

function updateIVR(state) {
    if (speechUtterance) {
        speechSynthesis.cancel();
    }
    document.getElementById("ivrScreen").innerText = ivrFlow[state].message;
    speak(ivrFlow[state].message);
    startListening(state);
}

function startListening(state) {
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.onresult = function(event) {
        const speechResult = event.results[0][0].transcript.trim();
        console.log("Recognized: ", speechResult);
        if (ivrFlow[state].options) {
            Object.entries(ivrFlow[state].options).forEach(([key, nextState]) => {
                if (speechResult.includes(key)) {
                    updateIVR(nextState);
                }
            });
        }
    };
    recognition.start();
}

function visualizeAudio() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        const audioContext = new AudioContext();
        const analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        analyser.fftSize = 256;
        const canvas = document.getElementById("spectrogram");
        const ctx = canvas.getContext("2d");
        function draw() {
            requestAnimationFrame(draw);
            const dataArray = new Uint8Array(analyser.frequencyBinCount);
            analyser.getByteFrequencyData(dataArray);
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = "lime";
            dataArray.forEach((value, index) => {
                ctx.fillRect(index * 3, canvas.height - value, 2, value);
            });
        }
        draw();
    });
}
visualizeAudio();
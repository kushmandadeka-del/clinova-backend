const micButton = document.getElementById("mic-btn");
const micStatus = document.getElementById("mic-status");
const transcriptText = document.getElementById("transcript-text");
const languageSelect = document.getElementById("language-select");

const submitCaseButton = document.getElementById("submit-case-btn");

let currentTranscript = "";
let currentTranslation = "";
let currentCase = {};

let finalTranscript = "";
let isRecording = false;

const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;

if (!SpeechRecognition) {

    micStatus.innerText =
        "Speech recognition is not supported in this browser.";

} else {

    const recognition = new SpeechRecognition();

    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onstart = function () {

        console.log("Speech recognition started");

        isRecording = true;

        micStatus.innerText =
            "Listening... Speak now";

        micButton.innerText = "⏹️";
    };

    recognition.onresult = function (event) {

        let interimTranscript = "";

        for (
            let i = event.resultIndex;
            i < event.results.length;
            i++
        ) {

            const text =
                event.results[i][0].transcript;

            if (event.results[i].isFinal) {

                finalTranscript += text + " ";

            } else {

                interimTranscript += text;

            }
        }

        currentTranscript =
            (finalTranscript + interimTranscript).trim();

        transcriptText.innerText =
            currentTranscript;

        if (currentTranscript !== "") {

            fetch("/translate", {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/x-www-form-urlencoded"
                },

                body:
                    "text=" +
                    encodeURIComponent(currentTranscript) +
                    "&language=" +
                    encodeURIComponent(
                        languageSelect.value.split("-")[0]
                    )

            })

                .then(response => response.text())

                .then(translated => {

                    currentTranslation = translated;

                    document.getElementById(
                        "english-translation"
                    ).innerText = translated;

                    return fetch("/analyze", {

                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/x-www-form-urlencoded"
                        },

                        body:
                            "text=" +
                            encodeURIComponent(translated)

                    });

                })

                .then(response => response.json())

                .then(result => {

                    currentCase = result;

                    document.getElementById(
                        "symptoms"
                    ).innerText =
                        result.symptoms &&
                            result.symptoms.length > 0
                            ? result.symptoms.join(", ")
                            : "Not detected";

                    document.getElementById(
                        "duration"
                    ).innerText =
                        result.duration || "Not detected";

                    document.getElementById(
                        "medical-history"
                    ).innerText =
                        result.medical_history ||
                        "Not detected";

                    document.getElementById(
                        "medications"
                    ).innerText =
                        result.medications ||
                        "Not detected";

                    document.getElementById(
                        "allergies"
                    ).innerText =
                        result.allergies ||
                        "Not detected";

                })

                .catch(error => {

                    console.log(
                        "Translation/NLP error:",
                        error
                    );

                });
        }
    };

    recognition.onerror = function (event) {

        console.log(
            "Speech recognition error:",
            event.error
        );

        micStatus.innerText =
            "Error: " + event.error;

        micButton.innerText = "🎤";

        isRecording = false;
    };

    recognition.onend = function () {

        console.log(
            "Speech recognition ended"
        );

        isRecording = false;

        micStatus.innerText =
            "Tap to start recording";

        micButton.innerText = "🎤";
    };

    micButton.addEventListener(
        "click",
        function () {

            if (!isRecording) {

                finalTranscript = "";
                currentTranscript = "";

                transcriptText.innerText = "";

                recognition.lang =
                    languageSelect.value;

                try {

                    recognition.start();

                } catch (error) {

                    console.log(
                        "Could not start recognition:",
                        error
                    );

                }

            } else {

                recognition.stop();

            }

        }
    );
}

if (submitCaseButton) {

    submitCaseButton.addEventListener(
        "click",
        function () {

            const patientSelect =
                document.getElementById(
                    "patient-select"
                );

            const doctorSelect =
                document.getElementById(
                    "doctor-select"
                );

            const submitStatus =
                document.getElementById(
                    "submit-status"
                );

            const patientId =
                patientSelect.value;

            const doctorId =
                doctorSelect.value;

            if (!patientId) {

                submitStatus.innerText =
                    "Please select a patient.";

                return;
            }

            if (!doctorId) {

                submitStatus.innerText =
                    "Please select a doctor.";

                return;
            }

            if (!currentTranscript) {

                submitStatus.innerText =
                    "Please record the patient's concern first.";

                return;
            }

            submitStatus.innerText =
                "Submitting case...";

            const formData =
                new URLSearchParams();

            formData.append(
                "patient_id",
                patientId
            );

            formData.append(
                "doctor_id",
                doctorId
            );

            formData.append(
                "original_transcript",
                currentTranscript
            );

            formData.append(
                "english_translation",
                currentTranslation
            );

            formData.append(
                "symptoms",
                currentCase.symptoms
                    ? currentCase.symptoms.join(", ")
                    : ""
            );

            formData.append(
                "duration",
                currentCase.duration || ""
            );

            formData.append(
                "medical_history",
                currentCase.medical_history || ""
            );

            formData.append(
                "medications",
                currentCase.medications || ""
            );

            formData.append(
                "allergies",
                currentCase.allergies || ""
            );

            fetch("/submit_case", {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/x-www-form-urlencoded"
                },

                body: formData.toString()

            })

                .then(response => {

                    return response.text();

                })

                .then(message => {

                    submitStatus.innerText =
                        message;

                })

                .catch(error => {

                    console.log(
                        "Submit error:",
                        error
                    );

                    submitStatus.innerText =
                        "Something went wrong while submitting the case.";

                });

        }
    );
}
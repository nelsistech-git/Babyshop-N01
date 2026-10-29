/* Public kiosk page (/face/attendance): face recognition in the browser. */
(function () {
    "use strict";

    var MODELS_URL = window.location.origin + "/sot_face_attendance/static/src/face_models";
    var MATCH_THRESHOLD = 0.3;      // lower = stricter
    var SCAN_INTERVAL_MS = 300;
    var TIMEOUT_MS = 60000;

    var modelsLoaded = false;
    var running = false;

    function $(id) {
        return document.getElementById(id);
    }

    function setStatus(text) {
        $("employee_attendance_status").textContent = text;
    }

    async function loadModels() {
        if (modelsLoaded) {
            return;
        }
        await Promise.all([
            faceapi.nets.faceRecognitionNet.loadFromUri(MODELS_URL),
            faceapi.nets.faceLandmark68Net.loadFromUri(MODELS_URL),
            faceapi.nets.ssdMobilenetv1.loadFromUri(MODELS_URL),
        ]);
        modelsLoaded = true;
    }

    function stopCamera() {
        if (window.localStream) {
            window.localStream.getTracks().forEach(function (track) {
                track.stop();
            });
            window.localStream = null;
        }
    }

    async function loadReferenceDescriptor(employeeId) {
        var img = await faceapi.fetchImage(
            window.location.origin + "/sot_face_attendance/employee_image/" + encodeURIComponent(employeeId)
        );
        var detection = await faceapi.detectSingleFace(img).withFaceLandmarks().withFaceDescriptor();
        if (!detection) {
            throw new Error("No face found in the employee photo");
        }
        return new faceapi.LabeledFaceDescriptors("known_person", [detection.descriptor]);
    }

    async function updateAttendance(employeeId) {
        try {
            var response = await fetch("/attendance/face/get_employees/" + encodeURIComponent(employeeId));
            if (!response.ok) {
                throw new Error("HTTP error! Status: " + response.status);
            }
            var data = await response.json();
            $("employee_name").textContent = data.name;
            setStatus(data.status ? "Checked In" : "Checked Out");
            if (data.last_check_in) {
                $("employee_work_hour").textContent = "Last check in: " + data.last_check_in + " (UTC)";
            }
            var image = $("employee_image");
            image.src = window.location.origin + "/sot_face_attendance/employee_image/" + data.id;
            image.style.display = "";
        } catch (error) {
            console.error("Fetch error:", error);
            setStatus("Attendance could not be recorded");
        }
    }

    window.face_recognition = async function () {
        var employeeId = $("face_employee_id").value.trim();
        if (running) {
            return;
        }
        if (!employeeId) {
            setStatus("Please enter the employee ID");
            return;
        }
        running = true;

        var video = $("videoInput");
        video.style.display = "block";
        setStatus("Loading...");

        try {
            await loadModels();
            var labeled = await loadReferenceDescriptor(employeeId);
            var matcher = new faceapi.FaceMatcher([labeled], MATCH_THRESHOLD);

            var stream = await navigator.mediaDevices.getUserMedia({ video: {} });
            window.localStream = stream;
            video.srcObject = stream;
            await video.play();
            setStatus("Look at the camera");

            var startedAt = Date.now();
            var busy = false;
            var interval = setInterval(async function () {
                if (busy) {
                    return;
                }
                busy = true;
                try {
                    var detections = await faceapi.detectAllFaces(video).withFaceLandmarks().withFaceDescriptors();
                    var matched = detections.some(function (d) {
                        return matcher.findBestMatch(d.descriptor).label !== "unknown";
                    });
                    if (matched) {
                        clearInterval(interval);
                        video.pause();
                        stopCamera();
                        video.style.display = "none";
                        running = false;
                        await updateAttendance(employeeId);
                    } else if (Date.now() - startedAt > TIMEOUT_MS) {
                        clearInterval(interval);
                        stopCamera();
                        video.style.display = "none";
                        running = false;
                        setStatus("Face not recognised, please try again");
                    }
                } catch (error) {
                    console.log("No Face Found");
                } finally {
                    busy = false;
                }
            }, SCAN_INTERVAL_MS);
        } catch (error) {
            console.error("Face recognition error:", error);
            stopCamera();
            video.style.display = "none";
            running = false;
            setStatus("Face recognition could not start");
        }
    };
})();

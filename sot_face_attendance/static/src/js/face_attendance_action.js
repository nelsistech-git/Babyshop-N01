/** @odoo-module **/

import { Component, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const MODELS_URL = `${window.location.origin}/sot_face_attendance/static/src/face_models`;
const FACE_API_URL = "/sot_face_attendance/static/src/js/face-api.min.js";
const MATCH_THRESHOLD = 0.4; // lower = stricter
const SCAN_INTERVAL_MS = 300;
const TIMEOUT_MS = 60000;

/**
 * Backend screen (Odoo 17, OWL) replacing the old "My Attendances" override:
 * the logged-in employee checks in / out by face.
 */
export class FaceAttendance extends Component {
    static template = "sot_face_attendance.FaceAttendance";
    static props = ["*"];

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.user = useService("user");
        this.videoRef = useRef("video");
        this.state = useState({
            loaded: false,
            employeeId: false,
            checkedIn: false,
            scanning: false,
            message: "",
        });
        this.interval = null;
        this.stream = null;

        onWillStart(async () => {
            await this.loadEmployee();
        });
        onWillUnmount(() => this.stopCamera());
    }

    async loadEmployee() {
        const data = await this.rpc("/hr_attendance/attendance_user_data");
        this.state.employeeId = data.id || false;
        this.state.checkedIn = data.attendance_state === "checked_in";
        this.state.loaded = true;
    }

    stopCamera() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
        if (this.stream) {
            this.stream.getTracks().forEach((track) => track.stop());
            this.stream = null;
        }
        this.state.scanning = false;
    }

    async loadModels() {
        if (!window.faceapi) {
            await loadJS(FACE_API_URL);
        }
        await Promise.all([
            faceapi.nets.faceRecognitionNet.loadFromUri(MODELS_URL),
            faceapi.nets.faceLandmark68Net.loadFromUri(MODELS_URL),
            faceapi.nets.ssdMobilenetv1.loadFromUri(MODELS_URL),
        ]);
    }

    async loadReferenceDescriptor() {
        const img = await faceapi.fetchImage(
            `${window.location.origin}/sot_face_attendance/employee_image/${this.state.employeeId}`
        );
        const detection = await faceapi.detectSingleFace(img).withFaceLandmarks().withFaceDescriptor();
        if (!detection) {
            throw new Error("No face found in the employee photo");
        }
        return new faceapi.LabeledFaceDescriptors("known_person", [detection.descriptor]);
    }

    async onFaceSignInOut() {
        if (this.state.scanning || !this.state.employeeId) {
            return;
        }
        this.state.scanning = true;
        this.state.message = _t("Loading...");
        try {
            await this.loadModels();
            const labeled = await this.loadReferenceDescriptor();
            const matcher = new faceapi.FaceMatcher([labeled], MATCH_THRESHOLD);

            this.stream = await navigator.mediaDevices.getUserMedia({ video: {} });
            const video = this.videoRef.el;
            video.srcObject = this.stream;
            await video.play();
            this.state.message = _t("Look at the camera");

            const startedAt = Date.now();
            let busy = false;
            this.interval = setInterval(async () => {
                if (busy) {
                    return;
                }
                busy = true;
                try {
                    const detections = await faceapi
                        .detectAllFaces(video)
                        .withFaceLandmarks()
                        .withFaceDescriptors();
                    const matched = detections.some(
                        (d) => matcher.findBestMatch(d.descriptor).label !== "unknown"
                    );
                    if (matched) {
                        this.stopCamera();
                        await this.checkInOut();
                    } else if (Date.now() - startedAt > TIMEOUT_MS) {
                        this.stopCamera();
                        this.state.message = _t("Face not recognised, please try again");
                    }
                } catch (error) {
                    console.log("No Face Found");
                } finally {
                    busy = false;
                }
            }, SCAN_INTERVAL_MS);
        } catch (error) {
            console.error("Face recognition error:", error);
            this.stopCamera();
            this.state.message = _t("Face recognition could not start");
        }
    }

    async checkInOut() {
        // Same server call as the standard systray check in / check out.
        await this.rpc("/hr_attendance/systray_check_in_out", { latitude: false, longitude: false });
        await this.loadEmployee();
        this.state.message = this.state.checkedIn ? _t("Checked In") : _t("Checked Out");
        this.notification.add(this.state.message, { type: "success" });
    }
}

registry.category("actions").add("sot_face_attendance.face_attendance_action", FaceAttendance);

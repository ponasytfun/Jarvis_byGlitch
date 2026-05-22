import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Item {
    id: root

    property var themePalette
    property string serifFontFamily: "Georgia"
    property string uiFontFamily: "Segoe UI"
    property var configObject: ({})
    property var audioDevices: []
    property var audioOutputDevices: []
    property var workflowNames: []

    signal saveRequested(var configObject)
    signal reloadRequested()
    signal openConfigRequested()
    signal openLogsRequested()
    signal testWorkflowRequested(var configObject)
    signal calibrateRequested(var configObject)
    signal refreshModelsRequested(var configObject)
    signal testMicrophoneRequested(var configObject)
    signal testTtsRequested(var configObject)
    signal testAiRequested(var configObject)
    signal testSttRequested(var configObject)

    function workflowIndex() {
        if (!root.configObject || !root.configObject.runtime)
            return 0
        for (var i = 0; i < root.workflowNames.length; i++) {
            if (root.workflowNames[i] === root.configObject.runtime.default_workflow)
                return i
        }
        return 0
    }

    function surfaceThemeIndex() {
        return root.configObject && root.configObject.ui && root.configObject.ui.theme === "light" ? 1 : 0
    }

    function atomThemeIndex() {
        if (!root.configObject || !root.configObject.ui)
            return 2
        switch (root.configObject.ui.atom_theme) {
        case "nuclear_waste":
            return 0
        case "blood_red":
            return 1
        default:
            return 2
        }
    }

    function deviceIndex() {
        if (!root.configObject || !root.configObject.audio)
            return 0
        for (var i = 0; i < root.audioDevices.length; i++) {
            if (root.audioDevices[i].index === root.configObject.audio.device_index)
                return i
        }
        return 0
    }

    function outputDeviceIndex() {
        if (!root.configObject || !root.configObject.voice)
            return 0
        for (var i = 0; i < root.audioOutputDevices.length; i++) {
            if (root.audioOutputDevices[i].index === root.configObject.voice.output_device_index)
                return i
        }
        return 0
    }

    function aiProviderIndex() {
        if (!root.configObject || !root.configObject.ai)
            return 0
        switch (root.configObject.ai.provider) {
        case "lm_studio":
            return 1
        case "ollama":
            return 2
        default:
            return 0
        }
    }

    function ttsBackendIndex() {
        if (!root.configObject || !root.configObject.voice)
            return 0
        switch (root.configObject.voice.tts_backend) {
        case "kokoro":
            return 1
        case "piper":
            return 2
        case "sapi":
            return 3
        default:
            return 0
        }
    }

    function csvOrBlank(value) {
        return value && value.length ? value.join(", ") : ""
    }

    function parseCsv(value) {
        var items = value.split(",")
        var cleaned = []
        for (var i = 0; i < items.length; i++) {
            var item = items[i].trim()
            if (item.length)
                cleaned.push(item)
        }
        return cleaned
    }

    onConfigObjectChanged: {
        if (typeof workflowCombo !== "undefined")
            workflowCombo.currentIndex = workflowIndex()
        if (typeof surfaceThemeCombo !== "undefined")
            surfaceThemeCombo.currentIndex = surfaceThemeIndex()
        if (typeof atomThemeCombo !== "undefined")
            atomThemeCombo.currentIndex = atomThemeIndex()
        if (typeof deviceCombo !== "undefined")
            deviceCombo.currentIndex = deviceIndex()
        if (typeof outputDeviceCombo !== "undefined")
            outputDeviceCombo.currentIndex = outputDeviceIndex()
        if (typeof aiProviderCombo !== "undefined")
            aiProviderCombo.currentIndex = aiProviderIndex()
        if (typeof ttsBackendCombo !== "undefined")
            ttsBackendCombo.currentIndex = ttsBackendIndex()
        if (typeof sttDeviceCombo !== "undefined")
            sttDeviceCombo.currentIndex = Math.max(0, sttDeviceCombo.model.indexOf(root.configObject.voice ? root.configObject.voice.stt_device : "auto"))
        if (typeof logLevelCombo !== "undefined")
            logLevelCombo.currentIndex = Math.max(0, logLevelCombo.model.indexOf(root.configObject.debug ? root.configObject.debug.log_level : "INFO"))
    }

    Rectangle {
        anchors.fill: parent
        radius: 30
        color: root.themePalette.heroSurface
        border.width: 1
        border.color: root.themePalette.cardBorder
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 18

        Rectangle {
            Layout.fillWidth: true
            radius: 26
            color: root.themePalette.cardBackgroundStrong
            border.width: 1
            border.color: root.themePalette.cardBorder

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 14

                RowLayout {
                    Layout.fillWidth: true

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3

                        Text {
                            text: "Configuration Nexus"
                            font.family: root.serifFontFamily
                            font.pixelSize: 30
                            font.weight: Font.DemiBold
                            color: root.themePalette.textPrimary
                        }

                        Text {
                            text: "Tune the uranium command core, local voice stack, clap trigger, music workflow, and desktop targets."
                            wrapMode: Text.Wrap
                            font.family: root.uiFontFamily
                            font.pixelSize: 13
                            color: root.themePalette.textSecondary
                        }
                    }

                    RowLayout {
                        spacing: 10

                        ActionButton {
                            text: "Save Config"
                            tone: "primary"
                            themePalette: root.themePalette
                            uiFontFamily: root.uiFontFamily
                            onClicked: root.saveRequested(root.configObject)
                        }

                        ActionButton {
                            text: "Reload Config"
                            tone: "secondary"
                            themePalette: root.themePalette
                            uiFontFamily: root.uiFontFamily
                            onClicked: root.reloadRequested()
                        }

                        ActionButton {
                            text: "Open Config Folder"
                            tone: "quiet"
                            themePalette: root.themePalette
                            uiFontFamily: root.uiFontFamily
                            onClicked: root.openConfigRequested()
                        }

                        ActionButton {
                            text: "Open Logs Folder"
                            tone: "quiet"
                            themePalette: root.themePalette
                            uiFontFamily: root.uiFontFamily
                            onClicked: root.openLogsRequested()
                        }

                        ActionButton {
                            text: "Test Workflow"
                            tone: "secondary"
                            themePalette: root.themePalette
                            uiFontFamily: root.uiFontFamily
                            onClicked: root.testWorkflowRequested(root.configObject)
                        }

                        ActionButton {
                            text: "Refresh Local Models"
                            tone: "secondary"
                            themePalette: root.themePalette
                            uiFontFamily: root.uiFontFamily
                            onClicked: root.refreshModelsRequested(root.configObject)
                        }

                        ActionButton {
                            text: "Test Microphone"
                            tone: "quiet"
                            themePalette: root.themePalette
                            uiFontFamily: root.uiFontFamily
                            onClicked: root.testMicrophoneRequested(root.configObject)
                        }

                        ActionButton {
                            text: "Test STT"
                            tone: "quiet"
                            themePalette: root.themePalette
                            uiFontFamily: root.uiFontFamily
                            onClicked: root.testSttRequested(root.configObject)
                        }

                        ActionButton {
                            text: "Test TTS"
                            tone: "quiet"
                            themePalette: root.themePalette
                            uiFontFamily: root.uiFontFamily
                            onClicked: root.testTtsRequested(root.configObject)
                        }

                        ActionButton {
                            text: "Test AI"
                            tone: "quiet"
                            themePalette: root.themePalette
                            uiFontFamily: root.uiFontFamily
                            onClicked: root.testAiRequested(root.configObject)
                        }
                    }
                }
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            Item {
                width: root.width - 44
                implicitHeight: settingsGrid.implicitHeight + 24

                GridLayout {
                    id: settingsGrid
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    columns: 2
                    rowSpacing: 16
                    columnSpacing: 16

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        radius: 24
                        color: root.themePalette.cardBackgroundStrong
                        border.width: 1
                        border.color: root.themePalette.cardBorder
                        implicitHeight: sessionColumn.implicitHeight + 28

                        ColumnLayout {
                            id: sessionColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            Text {
                                text: "Session and Visual Theme"
                                font.family: root.serifFontFamily
                                font.pixelSize: 20
                                color: root.themePalette.textPrimary
                            }

                            Label { text: "Workflow"; font.family: root.uiFontFamily }
                            ComboBox {
                                id: workflowCombo
                                Layout.fillWidth: true
                                model: root.workflowNames
                                Component.onCompleted: currentIndex = root.workflowIndex()
                                onActivated: root.configObject.runtime.default_workflow = currentText
                            }

                            Label { text: "Surface Theme"; font.family: root.uiFontFamily }
                            ComboBox {
                                id: surfaceThemeCombo
                                Layout.fillWidth: true
                                model: ["dark", "light"]
                                Component.onCompleted: currentIndex = root.surfaceThemeIndex()
                                onActivated: root.configObject.ui.theme = currentText
                            }

                            Label { text: "Atom Theme"; font.family: root.uiFontFamily }
                            ComboBox {
                                id: atomThemeCombo
                                Layout.fillWidth: true
                                model: [
                                    { "label": "Nuclear Waste", "value": "nuclear_waste" },
                                    { "label": "Blood Red", "value": "blood_red" },
                                    { "label": "Cold Blue", "value": "cold_blue" }
                                ]
                                textRole: "label"
                                Component.onCompleted: currentIndex = root.atomThemeIndex()
                                onActivated: root.configObject.ui.atom_theme = model[currentIndex].value
                            }

                            CheckBox {
                                text: "Dry run mode"
                                checked: root.configObject.runtime ? root.configObject.runtime.dry_run : false
                                onToggled: root.configObject.runtime.dry_run = checked
                            }

                            CheckBox {
                                text: "Enable UI animation"
                                checked: root.configObject.ui ? root.configObject.ui.animations_enabled : true
                                onToggled: root.configObject.ui.animations_enabled = checked
                            }

                            CheckBox {
                                text: "Save chat history between launches"
                                checked: root.configObject.ui ? root.configObject.ui.chat_history_enabled : true
                                onToggled: root.configObject.ui.chat_history_enabled = checked
                            }

                            CheckBox {
                                text: "Show diagnostics panel"
                                checked: root.configObject.ui ? root.configObject.ui.show_debug_panel : true
                                onToggled: root.configObject.ui.show_debug_panel = checked
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        radius: 24
                        color: root.themePalette.cardBackgroundStrong
                        border.width: 1
                        border.color: root.themePalette.cardBorder
                        implicitHeight: musicColumn.implicitHeight + 28

                        ColumnLayout {
                            id: musicColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            Text {
                                text: "The Clash Automation"
                                font.family: root.serifFontFamily
                                font.pixelSize: 20
                                color: root.themePalette.textPrimary
                            }

                            Text {
                                text: "A direct YouTube Music track URL is the reliable path. Search fallback remains best-effort only."
                                wrapMode: Text.Wrap
                                font.family: root.uiFontFamily
                                font.pixelSize: 12
                                color: root.themePalette.textSecondary
                            }

                            Label { text: "Music query"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.music ? root.configObject.music.music_query : ""
                                onEditingFinished: root.configObject.music.music_query = text
                            }

                            Label { text: "Direct music URL"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.music ? root.configObject.music.music_url : ""
                                onEditingFinished: root.configObject.music.music_url = text
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                rowSpacing: 8
                                columnSpacing: 10

                                Label { text: "Open delay ms"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.music ? String(root.configObject.music.post_open_delay_ms) : "3200"
                                    onEditingFinished: root.configObject.music.post_open_delay_ms = parseInt(text)
                                }

                                Label { text: "Playback timeout ms"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.music ? String(root.configObject.music.playback_start_timeout_ms) : "6000"
                                    onEditingFinished: root.configObject.music.playback_start_timeout_ms = parseInt(text)
                                }
                            }

                            CheckBox {
                                text: "Use media key fallback"
                                checked: root.configObject.music ? root.configObject.music.use_media_key_fallback : false
                                onToggled: root.configObject.music.use_media_key_fallback = checked
                            }

                            CheckBox {
                                text: "Use safe play shortcut fallback"
                                checked: root.configObject.music ? root.configObject.music.use_play_shortcut_fallback : false
                                onToggled: root.configObject.music.use_play_shortcut_fallback = checked
                            }

                            CheckBox {
                                text: "Verify playback best effort"
                                checked: root.configObject.music ? root.configObject.music.verify_playback_best_effort : true
                                onToggled: root.configObject.music.verify_playback_best_effort = checked
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        radius: 24
                        color: root.themePalette.cardBackgroundStrong
                        border.width: 1
                        border.color: root.themePalette.cardBorder
                        implicitHeight: micColumn.implicitHeight + 28

                        ColumnLayout {
                            id: micColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            Text {
                                text: "Microphone and Clap Trigger"
                                font.family: root.serifFontFamily
                                font.pixelSize: 20
                                color: root.themePalette.textPrimary
                            }

                            Label { text: "Input device"; font.family: root.uiFontFamily }
                            ComboBox {
                                id: deviceCombo
                                Layout.fillWidth: true
                                model: root.audioDevices
                                textRole: "label"
                                Component.onCompleted: currentIndex = root.deviceIndex()
                                onActivated: root.configObject.audio.device_index = root.audioDevices[currentIndex].index
                            }

                            ActionButton {
                                text: "Calibrate Microphone"
                                tone: "secondary"
                                themePalette: root.themePalette
                                uiFontFamily: root.uiFontFamily
                                onClicked: root.calibrateRequested(root.configObject)
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                rowSpacing: 8
                                columnSpacing: 10

                                Label { text: "Clap count"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.trigger ? String(root.configObject.trigger.clap_count) : "3"
                                    onEditingFinished: root.configObject.trigger.clap_count = parseInt(text)
                                }

                                Label { text: "Window sec"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.trigger ? String(root.configObject.trigger.window_seconds) : "2.5"
                                    onEditingFinished: root.configObject.trigger.window_seconds = parseFloat(text)
                                }

                                Label { text: "Min gap ms"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.trigger ? String(root.configObject.trigger.min_clap_gap_ms) : "120"
                                    onEditingFinished: root.configObject.trigger.min_clap_gap_ms = parseInt(text)
                                }

                                Label { text: "Max gap ms"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.trigger ? String(root.configObject.trigger.max_clap_gap_ms) : "900"
                                    onEditingFinished: root.configObject.trigger.max_clap_gap_ms = parseInt(text)
                                }

                                Label { text: "Threshold"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.trigger ? String(root.configObject.trigger.amplitude_threshold) : "0.12"
                                    onEditingFinished: root.configObject.trigger.amplitude_threshold = parseFloat(text)
                                }

                                Label { text: "Cooldown sec"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.trigger ? String(root.configObject.trigger.cooldown_seconds) : "10"
                                    onEditingFinished: root.configObject.trigger.cooldown_seconds = parseFloat(text)
                                }

                                Label { text: "Calibration sec"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.audio ? String(root.configObject.audio.calibration_seconds) : "2.0"
                                    onEditingFinished: root.configObject.audio.calibration_seconds = parseFloat(text)
                                }

                                Label { text: "Sample rate"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.audio ? String(root.configObject.audio.sample_rate) : "16000"
                                    onEditingFinished: root.configObject.audio.sample_rate = parseInt(text)
                                }
                            }

                            CheckBox {
                                text: "Auto calibrate noise floor"
                                checked: root.configObject.trigger ? root.configObject.trigger.noise_floor_auto_calibrate : true
                                onToggled: root.configObject.trigger.noise_floor_auto_calibrate = checked
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        radius: 24
                        color: root.themePalette.cardBackgroundStrong
                        border.width: 1
                        border.color: root.themePalette.cardBorder
                        implicitHeight: voiceColumn.implicitHeight + 28

                        ColumnLayout {
                            id: voiceColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            Text {
                                text: "Local Voice Stack"
                                font.family: root.serifFontFamily
                                font.pixelSize: 20
                                color: root.themePalette.textPrimary
                            }

                            Text {
                                text: "Preferred local stack: faster-whisper for STT, Kokoro or Piper for TTS, and LM Studio first with Ollama fallback for the local AI brain. Python 3.11 or 3.12 is recommended for the full speech stack."
                                wrapMode: Text.Wrap
                                font.family: root.uiFontFamily
                                font.pixelSize: 12
                                color: root.themePalette.textSecondary
                            }

                            CheckBox {
                                text: "Enable voice layer"
                                checked: root.configObject.voice ? root.configObject.voice.enabled : false
                                onToggled: root.configObject.voice.enabled = checked
                            }

                            CheckBox {
                                text: "Enable click-to-talk"
                                checked: root.configObject.voice ? root.configObject.voice.click_to_talk_enabled : true
                                onToggled: root.configObject.voice.click_to_talk_enabled = checked
                            }

                            CheckBox {
                                text: "Auto-arm voice when listening starts"
                                checked: root.configObject.voice ? root.configObject.voice.auto_start_with_listening : false
                                onToggled: root.configObject.voice.auto_start_with_listening = checked
                            }

                            CheckBox {
                                text: "Use wake-word / wake-phrase gating"
                                checked: root.configObject.voice ? root.configObject.voice.wake_word_enabled : false
                                onToggled: root.configObject.voice.wake_word_enabled = checked
                            }

                            CheckBox {
                                text: "Speak responses aloud"
                                checked: root.configObject.voice ? root.configObject.voice.speak_responses : true
                                onToggled: root.configObject.voice.speak_responses = checked
                            }

                            CheckBox {
                                text: "Enable VAD-guided speech capture"
                                checked: root.configObject.voice ? root.configObject.voice.vad_enabled : true
                                onToggled: root.configObject.voice.vad_enabled = checked
                            }

                            Label { text: "Wake phrases"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.voice ? root.csvOrBlank(root.configObject.voice.wake_phrases) : "hey jarvis, jarvis activate"
                                onEditingFinished: root.configObject.voice.wake_phrases = root.parseCsv(text)
                            }

                            Label { text: "Deactivate phrases"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.voice ? root.csvOrBlank(root.configObject.voice.deactivate_phrases) : "jarvis deactivate"
                                onEditingFinished: root.configObject.voice.deactivate_phrases = root.parseCsv(text)
                            }

                            Label { text: "Output device"; font.family: root.uiFontFamily }
                            ComboBox {
                                id: outputDeviceCombo
                                Layout.fillWidth: true
                                model: root.audioOutputDevices
                                textRole: "label"
                                Component.onCompleted: currentIndex = root.outputDeviceIndex()
                                onActivated: root.configObject.voice.output_device_index = root.audioOutputDevices[currentIndex].index
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                rowSpacing: 8
                                columnSpacing: 10

                                Label { text: "Wake threshold"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.voice ? String(root.configObject.voice.wake_threshold) : "0.52"
                                    onEditingFinished: root.configObject.voice.wake_threshold = parseFloat(text)
                                }

                                Label { text: "Speech threshold"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.voice ? String(root.configObject.voice.speech_threshold) : "0.018"
                                    onEditingFinished: root.configObject.voice.speech_threshold = parseFloat(text)
                                }

                                Label { text: "VAD sensitivity"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.voice ? String(root.configObject.voice.vad_sensitivity) : "0.55"
                                    onEditingFinished: root.configObject.voice.vad_sensitivity = parseFloat(text)
                                }

                                Label { text: "Listen timeout sec"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.voice ? String(root.configObject.voice.listen_timeout_seconds) : "15.0"
                                    onEditingFinished: root.configObject.voice.listen_timeout_seconds = parseFloat(text)
                                }

                                Label { text: "Silence timeout sec"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.voice ? String(root.configObject.voice.silence_timeout_seconds) : "1.2"
                                    onEditingFinished: {
                                        root.configObject.voice.silence_timeout_seconds = parseFloat(text)
                                        root.configObject.voice.silence_timeout_ms = Math.round(parseFloat(text) * 1000)
                                    }
                                }

                                Label { text: "Min record sec"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.voice ? String(root.configObject.voice.min_record_seconds) : "0.5"
                                    onEditingFinished: root.configObject.voice.min_record_seconds = parseFloat(text)
                                }

                                Label { text: "Max record sec"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.voice ? String(root.configObject.voice.max_record_seconds) : "20"
                                    onEditingFinished: {
                                        root.configObject.voice.max_record_seconds = parseFloat(text)
                                        root.configObject.voice.max_utterance_seconds = parseFloat(text)
                                    }
                                }

                                Label { text: "STT model"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.voice ? root.configObject.voice.stt_model : "base.en"
                                    onEditingFinished: root.configObject.voice.stt_model = text
                                }

                                Label { text: "STT device"; font.family: root.uiFontFamily }
                                ComboBox {
                                    id: sttDeviceCombo
                                    model: ["auto", "cpu", "cuda"]
                                    onActivated: root.configObject.voice.stt_device = currentText
                                    Component.onCompleted: currentIndex = Math.max(0, model.indexOf(root.configObject.voice ? root.configObject.voice.stt_device : "auto"))
                                }

                                Label { text: "TTS backend"; font.family: root.uiFontFamily }
                                ComboBox {
                                    id: ttsBackendCombo
                                    model: [
                                        { "label": "auto", "value": "auto" },
                                        { "label": "kokoro", "value": "kokoro" },
                                        { "label": "piper", "value": "piper" },
                                        { "label": "sapi", "value": "sapi" }
                                    ]
                                    textRole: "label"
                                    Component.onCompleted: currentIndex = root.ttsBackendIndex()
                                    onActivated: root.configObject.voice.tts_backend = model[currentIndex].value
                                }

                                Label { text: "TTS voice"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.voice ? root.configObject.voice.tts_voice : "bf_emma"
                                    onEditingFinished: root.configObject.voice.tts_voice = text
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        radius: 24
                        color: root.themePalette.cardBackgroundStrong
                        border.width: 1
                        border.color: root.themePalette.cardBorder
                        implicitHeight: targetsColumn.implicitHeight + 28

                        ColumnLayout {
                            id: targetsColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            Text {
                                text: "Desktop Targets"
                                font.family: root.serifFontFamily
                                font.pixelSize: 20
                                color: root.themePalette.textPrimary
                            }

                            Label { text: "Brave path"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.paths ? root.configObject.paths.brave_path : ""
                                onEditingFinished: root.configObject.paths.brave_path = text
                            }

                            Label { text: "VS Code path"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.paths ? root.configObject.paths.vscode_path : ""
                                onEditingFinished: root.configObject.paths.vscode_path = text
                            }

                            Label { text: "Discord path"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.paths ? root.configObject.paths.discord_path : ""
                                onEditingFinished: root.configObject.paths.discord_path = text
                            }

                            Label { text: "OBS path"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.paths ? root.configObject.paths.obs_path : ""
                                onEditingFinished: root.configObject.paths.obs_path = text
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        radius: 24
                        color: root.themePalette.cardBackgroundStrong
                        border.width: 1
                        border.color: root.themePalette.cardBorder
                        implicitHeight: integrationColumn.implicitHeight + 28

                        ColumnLayout {
                            id: integrationColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            Text {
                                text: "Local AI Brain and Speech Assets"
                                font.family: root.serifFontFamily
                                font.pixelSize: 20
                                color: root.themePalette.textPrimary
                            }

                            Label { text: "AI provider"; font.family: root.uiFontFamily }
                            ComboBox {
                                id: aiProviderCombo
                                Layout.fillWidth: true
                                model: [
                                    { "label": "auto", "value": "auto" },
                                    { "label": "lm_studio", "value": "lm_studio" },
                                    { "label": "ollama", "value": "ollama" }
                                ]
                                textRole: "label"
                                Component.onCompleted: currentIndex = root.aiProviderIndex()
                                onActivated: root.configObject.ai.provider = model[currentIndex].value
                            }

                            Label { text: "AI base URL override"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.ai ? root.configObject.ai.base_url : ""
                                onEditingFinished: root.configObject.ai.base_url = text
                            }

                            Label { text: "Preferred model name"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.ai ? root.configObject.ai.model_name : ""
                                onEditingFinished: root.configObject.ai.model_name = text
                            }

                            CheckBox {
                                text: "Enable safe tool routing"
                                checked: root.configObject.ai ? root.configObject.ai.tool_routing_enabled : true
                                onToggled: root.configObject.ai.tool_routing_enabled = checked
                            }

                            CheckBox {
                                text: "Use streaming replies when available"
                                checked: root.configObject.ai ? root.configObject.ai.stream_enabled : false
                                onToggled: root.configObject.ai.stream_enabled = checked
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "AI status: " + bridge.aiStatusText
                                wrapMode: Text.Wrap
                                font.family: root.uiFontFamily
                                font.pixelSize: 12
                                color: root.themePalette.textSecondary
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: bridge.aiErrorText.length > 0
                                text: "Last AI error: " + bridge.aiErrorText
                                wrapMode: Text.Wrap
                                font.family: root.uiFontFamily
                                font.pixelSize: 12
                                color: root.themePalette.danger
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "AI base URL: " + (bridge.aiBaseUrl.length > 0 ? bridge.aiBaseUrl : "(none)")
                                wrapMode: Text.Wrap
                                font.family: root.uiFontFamily
                                font.pixelSize: 12
                                color: root.themePalette.textSecondary
                            }

                            Text {
                                Layout.fillWidth: true
                                text: bridge.aiAvailableModels.length > 0
                                      ? "Detected local models: " + bridge.aiAvailableModels.join(", ")
                                      : "Detected local models: none"
                                wrapMode: Text.Wrap
                                font.family: root.uiFontFamily
                                font.pixelSize: 12
                                color: root.themePalette.textSecondary
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                rowSpacing: 8
                                columnSpacing: 10

                                Label { text: "Temperature"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.ai ? String(root.configObject.ai.temperature) : "0.35"
                                    onEditingFinished: root.configObject.ai.temperature = parseFloat(text)
                                }

                                Label { text: "Max tokens"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.ai ? String(root.configObject.ai.max_tokens) : "220"
                                    onEditingFinished: root.configObject.ai.max_tokens = parseInt(text)
                                }
                            }

                            Label { text: "Wake-word model path (optional)"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.voice ? root.configObject.voice.wake_word_model_path : ""
                                onEditingFinished: root.configObject.voice.wake_word_model_path = text
                            }

                            Label { text: "Kokoro model path"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.voice ? root.configObject.voice.tts_model_path : ""
                                onEditingFinished: root.configObject.voice.tts_model_path = text
                            }

                            Label { text: "Kokoro voices path"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.voice ? root.configObject.voice.tts_voices_path : ""
                                onEditingFinished: root.configObject.voice.tts_voices_path = text
                            }

                            Label { text: "Piper executable path"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.voice ? root.configObject.voice.piper_exe_path : ""
                                onEditingFinished: root.configObject.voice.piper_exe_path = text
                            }

                            Label { text: "Piper model path"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.voice ? root.configObject.voice.piper_model_path : ""
                                onEditingFinished: root.configObject.voice.piper_model_path = text
                            }

                            Label { text: "LM Studio base URL"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.ai ? root.configObject.ai.lm_studio_base_url : "http://127.0.0.1:1234/v1"
                                onEditingFinished: root.configObject.ai.lm_studio_base_url = text
                            }

                            Label { text: "LM Studio alt URL"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.ai ? root.configObject.ai.lm_studio_alt_base_url : "http://127.0.0.1:1234/api/v1"
                                onEditingFinished: root.configObject.ai.lm_studio_alt_base_url = text
                            }

                            Label { text: "Ollama base URL"; font.family: root.uiFontFamily }
                            TextField {
                                Layout.fillWidth: true
                                text: root.configObject.ai ? root.configObject.ai.ollama_base_url : "http://127.0.0.1:11434"
                                onEditingFinished: root.configObject.ai.ollama_base_url = text
                            }

                            CheckBox {
                                text: "Allow Ollama fallback when LM Studio is unavailable"
                                checked: root.configObject.ai ? root.configObject.ai.allow_ollama_fallback : true
                                onToggled: root.configObject.ai.allow_ollama_fallback = checked
                            }

                            Label { text: "Jarvis system prompt"; font.family: root.uiFontFamily }
                            TextArea {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 120
                                wrapMode: TextEdit.Wrap
                                text: root.configObject.ai ? root.configObject.ai.system_prompt : ""
                                onFocusChanged: {
                                    if (!focus)
                                        root.configObject.ai.system_prompt = text
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        radius: 24
                        color: root.themePalette.cardBackgroundStrong
                        border.width: 1
                        border.color: root.themePalette.cardBorder
                        implicitHeight: debugColumn.implicitHeight + 28

                        ColumnLayout {
                            id: debugColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            Text {
                                text: "Debug and Diagnostics"
                                font.family: root.serifFontFamily
                                font.pixelSize: 20
                                color: root.themePalette.textPrimary
                            }

                            CheckBox {
                                text: "Save audio debug WAV files"
                                checked: root.configObject.debug ? root.configObject.debug.save_audio_debug_files : false
                                onToggled: root.configObject.debug.save_audio_debug_files = checked
                            }

                            CheckBox {
                                text: "Save speech transcripts to logs"
                                checked: root.configObject.debug ? root.configObject.debug.save_transcripts : true
                                onToggled: {
                                    root.configObject.debug.save_transcripts = checked
                                    root.configObject.voice.log_transcripts = checked
                                }
                            }

                            Label { text: "Log level"; font.family: root.uiFontFamily }
                            ComboBox {
                                id: logLevelCombo
                                model: ["DEBUG", "INFO", "WARNING", "ERROR"]
                                onActivated: {
                                    root.configObject.debug.log_level = currentText
                                    root.configObject.logging.level = currentText
                                }
                                Component.onCompleted: currentIndex = Math.max(0, model.indexOf(root.configObject.debug ? root.configObject.debug.log_level : "INFO"))
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignTop
                        radius: 24
                        color: root.themePalette.cardBackgroundStrong
                        border.width: 1
                        border.color: root.themePalette.cardBorder
                        implicitHeight: retryColumn.implicitHeight + 28

                        ColumnLayout {
                            id: retryColumn
                            anchors.fill: parent
                            anchors.margins: 14
                            spacing: 10

                            Text {
                                text: "Focus and Launch Hardening"
                                font.family: root.serifFontFamily
                                font.pixelSize: 20
                                color: root.themePalette.textPrimary
                            }

                            Text {
                                text: "These retries improve VS Code and Discord focus, relaunch, and side-by-side layout reliability."
                                wrapMode: Text.Wrap
                                font.family: root.uiFontFamily
                                font.pixelSize: 12
                                color: root.themePalette.textSecondary
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                columns: 2
                                rowSpacing: 8
                                columnSpacing: 10

                                Label { text: "VS Code retries"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.matching ? String(root.configObject.matching.vscode.focus_retry_count) : "3"
                                    onEditingFinished: root.configObject.matching.vscode.focus_retry_count = parseInt(text)
                                }

                                Label { text: "VS Code delay ms"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.matching ? String(root.configObject.matching.vscode.focus_retry_delay_ms) : "300"
                                    onEditingFinished: root.configObject.matching.vscode.focus_retry_delay_ms = parseInt(text)
                                }

                                Label { text: "VS Code timeout ms"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.matching ? String(root.configObject.matching.vscode.launch_timeout_ms) : "18000"
                                    onEditingFinished: root.configObject.matching.vscode.launch_timeout_ms = parseInt(text)
                                }

                                Label { text: "Discord retries"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.matching ? String(root.configObject.matching.discord.focus_retry_count) : "5"
                                    onEditingFinished: root.configObject.matching.discord.focus_retry_count = parseInt(text)
                                }

                                Label { text: "Discord delay ms"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.matching ? String(root.configObject.matching.discord.focus_retry_delay_ms) : "400"
                                    onEditingFinished: root.configObject.matching.discord.focus_retry_delay_ms = parseInt(text)
                                }

                                Label { text: "Discord timeout ms"; font.family: root.uiFontFamily }
                                TextField {
                                    text: root.configObject.matching ? String(root.configObject.matching.discord.launch_timeout_ms) : "22000"
                                    onEditingFinished: root.configObject.matching.discord.launch_timeout_ms = parseInt(text)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

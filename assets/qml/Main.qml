import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "components"

ApplicationWindow {
    id: root

    width: Math.max(1320, bridge.configData.ui ? bridge.configData.ui.window_width : 1480)
    height: Math.max(860, bridge.configData.ui ? bridge.configData.ui.window_height : 940)
    minimumWidth: 1280
    minimumHeight: 820
    visible: true
    title: bridge.configData.app ? bridge.configData.app.name : "JarvisAssistant"
    color: "transparent"

    readonly property var themePalette: bridge.themePalette
    property var workingConfig: ({})
    property string toastTitle: ""
    property string toastMessage: ""
    property var viewOrder: ["home", "listening", "executing", "settings", "logs"]

    function deepClone(value) {
        if (value === undefined || value === null)
            return ({})
        return JSON.parse(JSON.stringify(value))
    }

    function viewIndex(viewName) {
        var idx = viewOrder.indexOf(viewName)
        return idx >= 0 ? idx : 0
    }

    function currentMicLabel() {
        if (!workingConfig.audio || !bridge.audioDevices || bridge.audioDevices.length === 0)
            return "Default system input"
        for (var i = 0; i < bridge.audioDevices.length; i++) {
            if (bridge.audioDevices[i].index === workingConfig.audio.device_index)
                return bridge.audioDevices[i].label
        }
        return bridge.audioDevices[0].label
    }

    function submitPromptFromComposer() {
        var text = promptComposer.text.trim()
        if (text.length === 0)
            return
        bridge.submitPrompt(text, root.workingConfig)
        promptComposer.text = ""
    }

    ListModel {
        id: logModel
    }

    Component.onCompleted: {
        workingConfig = deepClone(bridge.configData)
    }

    Connections {
        target: bridge

        function onConfigDataChanged() {
            root.workingConfig = root.deepClone(bridge.configData)
        }

        function onCurrentViewChanged() {
            pageFrame.opacity = 0
            pageFade.restart()
        }

        function onLogAppended(message) {
            logModel.append({ "text": message })
            if (logModel.count > 500)
                logModel.remove(0)
        }

        function onNotificationRequested(title, message) {
            root.toastTitle = title
            root.toastMessage = message
            toastPopup.open()
            toastTimer.restart()
        }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.themePalette.windowGradientStart }
            GradientStop { position: 0.5; color: root.themePalette.windowBackground }
            GradientStop { position: 1.0; color: root.themePalette.windowGradientEnd }
        }
    }

    Rectangle {
        width: 620
        height: 620
        radius: width / 2
        x: -200
        y: -240
        color: root.themePalette.atomBackdrop
        opacity: root.themePalette.name === "dark" ? 0.6 : 0.34
    }

    Rectangle {
        width: 520
        height: 520
        radius: width / 2
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: -120
        anchors.bottomMargin: -120
        color: Qt.rgba(1, 1, 1, root.themePalette.name === "dark" ? 0.04 : 0.4)
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 18

        HeaderBar {
            Layout.fillWidth: true
            Layout.preferredHeight: 92
            themePalette: root.themePalette
            titleText: workingConfig.app ? workingConfig.app.name : "JarvisAssistant"
            subtitleText: workingConfig.app ? workingConfig.app.subtitle : "Local desktop command core"
            currentView: bridge.currentView
            themeName: bridge.themeName
            serifFontFamily: bridge.serifFontFamily
            uiFontFamily: bridge.uiFontFamily

            onNavigateRequested: bridge.showView(viewName)
            onTestRequested: bridge.testWorkflow(root.workingConfig)
            onAdvancedRequested: bridge.showView("settings")
            onOpenLogsRequested: bridge.showView("logs")
            onDarkThemeRequested: {
                root.workingConfig.ui.theme = "dark"
                bridge.setTheme("dark")
            }
            onLightThemeRequested: {
                root.workingConfig.ui.theme = "light"
                bridge.setTheme("light")
            }
        }

        Item {
            id: pageFrame
            Layout.fillWidth: true
            Layout.fillHeight: true
            opacity: 1

            StackLayout {
                anchors.fill: parent
                currentIndex: root.viewIndex(bridge.currentView)

                Item {
                    id: homePage

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 18

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 230
                            radius: 30
                            color: root.themePalette.heroSurface
                            border.width: 1
                            border.color: root.themePalette.cardBorder
                            clip: true

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 26
                                spacing: 14

                                Text {
                                    text: "URANIUM-235 COMMAND CORE"
                                    font.family: bridge.uiFontFamily
                                    font.pixelSize: 11
                                    font.weight: Font.Medium
                                    font.letterSpacing: 2.6
                                    color: root.themePalette.accent
                                }

                                Text {
                                    text: "Jarvis Presence Matrix"
                                    font.family: bridge.serifFontFamily
                                    font.pixelSize: 50
                                    font.weight: Font.DemiBold
                                    color: root.themePalette.textPrimary
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: "A local desktop assistant with a stylized uranium atom core, clap-triggered automation, and a local-only AI stack that prefers LM Studio, falls back to Ollama, and can speak back with free local voice tools."
                                    wrapMode: Text.Wrap
                                    font.family: bridge.uiFontFamily
                                    font.pixelSize: 14
                                    lineHeight: 1.35
                                    color: root.themePalette.textSecondary
                                }

                                RowLayout {
                                    spacing: 8

                                    Repeater {
                                        model: [
                                            "Surface: " + bridge.themeName,
                                            "Atom: " + bridge.atomThemeName,
                                            "Workflow: " + (workingConfig.runtime ? workingConfig.runtime.default_workflow : "triple_clap_focus_mode")
                                        ]

                                        delegate: Rectangle {
                                            required property string modelData
                                            radius: 16
                                            color: root.themePalette.buttonQuietFill
                                            border.width: 1
                                            border.color: root.themePalette.cardBorder
                                            implicitHeight: 32
                                            implicitWidth: chipLabel.implicitWidth + 26

                                            Text {
                                                id: chipLabel
                                                anchors.centerIn: parent
                                                text: parent.modelData
                                                font.family: bridge.uiFontFamily
                                                font.pixelSize: 11
                                                color: root.themePalette.textSecondary
                                            }
                                        }
                                    }

                                    Item { Layout.fillWidth: true }

                                    ActionButton {
                                        text: "Start Listening"
                                        tone: "primary"
                                        themePalette: root.themePalette
                                        uiFontFamily: bridge.uiFontFamily
                                        onClicked: bridge.startListening(root.workingConfig)
                                    }

                                    ActionButton {
                                        text: "Talk to Jarvis"
                                        tone: "secondary"
                                        themePalette: root.themePalette
                                        uiFontFamily: bridge.uiFontFamily
                                        onClicked: bridge.startVoiceCapture(root.workingConfig)
                                    }

                                    ActionButton {
                                        text: "Refresh Local Models"
                                        tone: "secondary"
                                        themePalette: root.themePalette
                                        uiFontFamily: bridge.uiFontFamily
                                        onClicked: bridge.refreshModels(root.workingConfig)
                                    }

                                    ActionButton {
                                        text: "Test AI"
                                        tone: "quiet"
                                        themePalette: root.themePalette
                                        uiFontFamily: bridge.uiFontFamily
                                        onClicked: bridge.testAi(root.workingConfig)
                                    }

                                    ActionButton {
                                        text: "Advanced Settings"
                                        tone: "quiet"
                                        themePalette: root.themePalette
                                        uiFontFamily: bridge.uiFontFamily
                                        onClicked: bridge.showView("settings")
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 32
                            color: root.themePalette.heroSurface
                            border.width: 1
                            border.color: root.themePalette.cardBorder
                            clip: true

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 28
                                spacing: 14

                                Rectangle {
                                    Layout.alignment: Qt.AlignHCenter
                                    Layout.preferredWidth: Math.min(homePage.width - 120, 900)
                                    Layout.preferredHeight: 68
                                    radius: 22
                                    color: Qt.rgba(1, 1, 1, root.themePalette.name === "dark" ? 0.03 : 0.58)
                                    border.width: 1
                                    border.color: root.themePalette.cardBorder

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 14

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 2

                                            Text {
                                                text: bridge.workflowStepTitle
                                                font.family: bridge.uiFontFamily
                                                font.pixelSize: 14
                                                font.weight: Font.Medium
                                                color: root.themePalette.textPrimary
                                            }

                                            Text {
                                                text: bridge.workflowStepDetail
                                                elide: Text.ElideRight
                                                font.family: bridge.uiFontFamily
                                                font.pixelSize: 11
                                                color: root.themePalette.textMuted
                                            }
                                        }

                                        Rectangle {
                                            radius: 16
                                            implicitWidth: statusChip.implicitWidth + 22
                                            implicitHeight: 30
                                            color: root.themePalette.buttonPrimaryFill
                                            border.width: 1
                                            border.color: root.themePalette.accentSoft

                                            Text {
                                                id: statusChip
                                                anchors.centerIn: parent
                                                text: bridge.statusText
                                                font.family: bridge.uiFontFamily
                                                font.pixelSize: 11
                                                font.weight: Font.Medium
                                                color: root.themePalette.textPrimary
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.alignment: Qt.AlignHCenter
                                    Layout.preferredWidth: Math.min(homePage.width - 120, 980)
                                    radius: 22
                                    color: Qt.rgba(1, 1, 1, root.themePalette.name === "dark" ? 0.025 : 0.62)
                                    border.width: 1
                                    border.color: root.themePalette.cardBorder
                                    implicitHeight: statusFlow.implicitHeight + 26

                                    Flow {
                                        id: statusFlow
                                        anchors.fill: parent
                                        anchors.margins: 13
                                        spacing: 10

                                        Repeater {
                                            model: [
                                                { "title": "AI", "value": bridge.aiConnected ? "Connected" : "Disconnected" },
                                                { "title": "Provider", "value": bridge.aiProviderName },
                                                { "title": "Model", "value": bridge.aiModelName.length > 0 ? bridge.aiModelName : "None selected" },
                                                { "title": "Base URL", "value": bridge.aiBaseUrl.length > 0 ? bridge.aiBaseUrl : "None" },
                                                { "title": "Generating", "value": bridge.aiGenerating ? "Yes" : "No" },
                                                { "title": "Mic", "value": bridge.micStatusText },
                                                { "title": "TTS", "value": bridge.ttsStatusText }
                                            ]

                                            delegate: Rectangle {
                                                required property var modelData
                                                radius: 16
                                                color: root.themePalette.buttonQuietFill
                                                border.width: 1
                                                border.color: root.themePalette.cardBorder
                                                implicitHeight: statusColumn.implicitHeight + 16
                                                implicitWidth: Math.max(180, statusColumn.implicitWidth + 24)

                                                Column {
                                                    id: statusColumn
                                                    anchors.left: parent.left
                                                    anchors.right: parent.right
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    anchors.leftMargin: 12
                                                    anchors.rightMargin: 12
                                                    spacing: 2

                                                    Text {
                                                        text: parent.parent.modelData.title
                                                        font.family: bridge.uiFontFamily
                                                        font.pixelSize: 10
                                                        font.weight: Font.Medium
                                                        color: root.themePalette.textMuted
                                                    }

                                                    Text {
                                                        width: parent.width
                                                        text: parent.parent.modelData.value
                                                        wrapMode: Text.Wrap
                                                        maximumLineCount: 2
                                                        elide: Text.ElideRight
                                                        font.family: bridge.uiFontFamily
                                                        font.pixelSize: 11
                                                        color: root.themePalette.textSecondary
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                Item {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                }

                                OrbCore {
                                    Layout.alignment: Qt.AlignHCenter
                                    sizeFactor: 0.9
                                    themePalette: root.themePalette
                                    serifFontFamily: bridge.serifFontFamily
                                    uiFontFamily: bridge.uiFontFamily
                                    statusText: bridge.statusText
                                    workflowStepTitle: bridge.workflowStepTitle
                                    workflowStepDetail: bridge.workflowStepDetail
                                    listening: bridge.listening
                                    workflowRunning: bridge.workflowRunning
                                    signalLevel: bridge.signalLevel
                                    assistantState: bridge.assistantState
                                    immersive: false
                                    showLabels: true
                                    actionHint: bridge.voiceStatusText
                                    onToggleRequested: bridge.toggleListening(root.workingConfig)
                                }

                                Item {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                }

                                Rectangle {
                                    Layout.alignment: Qt.AlignHCenter
                                    Layout.preferredWidth: Math.min(homePage.width - 120, 960)
                                    Layout.fillWidth: true
                                    radius: 24
                                    color: Qt.rgba(1, 1, 1, root.themePalette.name === "dark" ? 0.03 : 0.58)
                                    border.width: 1
                                    border.color: root.themePalette.cardBorder
                                    Layout.preferredHeight: 360

                                    ColumnLayout {
                                        id: promptColumn
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 10

                                        Text {
                                            text: "Command Console"
                                            font.family: bridge.uiFontFamily
                                            font.pixelSize: 12
                                            font.weight: Font.Medium
                                            color: root.themePalette.textPrimary
                                        }

                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            radius: 20
                                            color: root.themePalette.cardBackgroundStrong
                                            border.width: 1
                                            border.color: root.themePalette.cardBorder

                                            ColumnLayout {
                                                anchors.fill: parent
                                                anchors.margins: 12
                                                spacing: 10

                                                RowLayout {
                                                    Layout.fillWidth: true

                                                    Text {
                                                        text: "Conversation Stream"
                                                        font.family: bridge.serifFontFamily
                                                        font.pixelSize: 24
                                                        color: root.themePalette.textPrimary
                                                    }

                                                    Item { Layout.fillWidth: true }

                                                    BusyIndicator {
                                                        running: bridge.aiGenerating
                                                        visible: running
                                                        implicitWidth: 28
                                                        implicitHeight: 28
                                                    }

                                                    ActionButton {
                                                        text: "Export Chat"
                                                        tone: "quiet"
                                                        themePalette: root.themePalette
                                                        uiFontFamily: bridge.uiFontFamily
                                                        onClicked: bridge.exportChat()
                                                    }

                                                    ActionButton {
                                                        text: "Clear Chat"
                                                        tone: "quiet"
                                                        themePalette: root.themePalette
                                                        uiFontFamily: bridge.uiFontFamily
                                                        onClicked: bridge.clearChat()
                                                    }
                                                }

                                                Rectangle {
                                                    Layout.fillWidth: true
                                                    Layout.fillHeight: true
                                                    radius: 18
                                                    color: Qt.rgba(1, 1, 1, root.themePalette.name === "dark" ? 0.018 : 0.72)
                                                    border.width: 1
                                                    border.color: root.themePalette.cardBorder

                                                    ListView {
                                                        id: chatList
                                                        anchors.fill: parent
                                                        anchors.margins: 12
                                                        spacing: 10
                                                        clip: true
                                                        model: bridge.chatMessages

                                                        onCountChanged: positionViewAtEnd()

                                                        delegate: Item {
                                                            required property var modelData
                                                            width: chatList.width
                                                            implicitHeight: bubble.implicitHeight + 8

                                                            Rectangle {
                                                                id: bubble
                                                                radius: 18
                                                                width: Math.min(chatList.width * 0.8, bubbleText.implicitWidth + 28)
                                                                implicitHeight: metaLabel.implicitHeight + bubbleText.implicitHeight + 18
                                                                anchors.right: modelData.role === "user" ? parent.right : undefined
                                                                anchors.left: modelData.role === "user" ? undefined : parent.left
                                                                color: modelData.role === "user"
                                                                       ? root.themePalette.buttonPrimaryFill
                                                                       : modelData.role === "assistant"
                                                                         ? root.themePalette.buttonQuietFill
                                                                         : Qt.rgba(1, 1, 1, root.themePalette.name === "dark" ? 0.05 : 0.86)
                                                                border.width: 1
                                                                border.color: modelData.role === "system"
                                                                              ? root.themePalette.cardBorder
                                                                              : (modelData.role === "user" ? root.themePalette.accentSoft : root.themePalette.cardBorder)

                                                                Column {
                                                                    anchors.fill: parent
                                                                    anchors.margins: 10
                                                                    spacing: 5

                                                                    Text {
                                                                        id: metaLabel
                                                                        text: (modelData.role === "user" ? "You" : (modelData.role === "assistant" ? "Jarvis" : "System"))
                                                                              + " | " + (modelData.timestamp || "")
                                                                        font.family: bridge.uiFontFamily
                                                                        font.pixelSize: 10
                                                                        font.weight: Font.Medium
                                                                        color: modelData.role === "user"
                                                                               ? root.themePalette.textPrimary
                                                                               : root.themePalette.textMuted
                                                                    }

                                                                    Text {
                                                                        id: bubbleText
                                                                        width: bubble.width - 20
                                                                        text: modelData.text
                                                                        wrapMode: Text.Wrap
                                                                        font.family: bridge.uiFontFamily
                                                                        font.pixelSize: 13
                                                                        color: modelData.role === "system"
                                                                               ? root.themePalette.textSecondary
                                                                               : root.themePalette.textPrimary
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }

                                                    Text {
                                                        anchors.centerIn: parent
                                                        visible: bridge.chatMessages.length === 0
                                                        text: "No conversation yet. Type or speak to Jarvis."
                                                        font.family: bridge.uiFontFamily
                                                        font.pixelSize: 12
                                                        color: root.themePalette.textMuted
                                                    }
                                                }

                                                Text {
                                                    Layout.fillWidth: true
                                                    visible: bridge.aiErrorText.length > 0
                                                    text: "AI issue: " + bridge.aiErrorText
                                                    wrapMode: Text.Wrap
                                                    font.family: bridge.uiFontFamily
                                                    font.pixelSize: 11
                                                    color: root.themePalette.danger
                                                }

                                                TextArea {
                                                    id: promptComposer
                                                    Layout.fillWidth: true
                                                    Layout.preferredHeight: 84
                                                    wrapMode: TextEdit.Wrap
                                                    placeholderText: "Type a message, command, or question for Jarvis..."
                                                    font.family: bridge.uiFontFamily
                                                    color: root.themePalette.textPrimary
                                                    selectByMouse: true
                                                    Keys.onPressed: function(event) {
                                                        if ((event.key === Qt.Key_Return || event.key === Qt.Key_Enter)
                                                                && !(event.modifiers & Qt.ShiftModifier)) {
                                                            root.submitPromptFromComposer()
                                                            event.accepted = true
                                                        }
                                                    }
                                                }

                                                Flow {
                                                    Layout.fillWidth: true
                                                    spacing: 10

                                                    ActionButton {
                                                        text: "Send"
                                                        tone: "primary"
                                                        themePalette: root.themePalette
                                                        uiFontFamily: bridge.uiFontFamily
                                                        onClicked: root.submitPromptFromComposer()
                                                    }

                                                    ActionButton {
                                                        text: bridge.listening ? "Stop Listening" : "Start Listening"
                                                        tone: bridge.listening ? "danger" : "secondary"
                                                        themePalette: root.themePalette
                                                        uiFontFamily: bridge.uiFontFamily
                                                        onClicked: bridge.listening ? bridge.stopListening() : bridge.startListening(root.workingConfig)
                                                    }

                                                    ActionButton {
                                                        text: "Talk"
                                                        tone: "secondary"
                                                        themePalette: root.themePalette
                                                        uiFontFamily: bridge.uiFontFamily
                                                        onClicked: bridge.startVoiceCapture(root.workingConfig)
                                                    }

                                                    ActionButton {
                                                        text: "Test Mic"
                                                        tone: "quiet"
                                                        themePalette: root.themePalette
                                                        uiFontFamily: bridge.uiFontFamily
                                                        onClicked: bridge.testMicrophone(root.workingConfig)
                                                    }

                                                    ActionButton {
                                                        text: "Test STT"
                                                        tone: "quiet"
                                                        themePalette: root.themePalette
                                                        uiFontFamily: bridge.uiFontFamily
                                                        onClicked: bridge.testStt(root.workingConfig)
                                                    }

                                                    ActionButton {
                                                        text: "Test AI"
                                                        tone: "quiet"
                                                        themePalette: root.themePalette
                                                        uiFontFamily: bridge.uiFontFamily
                                                        onClicked: bridge.testAi(root.workingConfig)
                                                    }

                                                    ActionButton {
                                                        text: "Test TTS"
                                                        tone: "quiet"
                                                        themePalette: root.themePalette
                                                        uiFontFamily: bridge.uiFontFamily
                                                        onClicked: bridge.testTts(root.workingConfig)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    id: listeningPage

                    Rectangle {
                        anchors.fill: parent
                        radius: 32
                        color: root.themePalette.heroSurface
                        border.width: 1
                        border.color: root.themePalette.cardBorder
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 30
                        spacing: 18

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Repeater {
                                model: [
                                    "Workflow: " + (workingConfig.runtime ? workingConfig.runtime.default_workflow : "triple_clap_focus_mode"),
                                    "AI: " + bridge.aiProviderName,
                                    bridge.micStatusText,
                                    bridge.voiceStatusText
                                ]

                                delegate: Rectangle {
                                    required property string modelData
                                    radius: 18
                                    color: root.themePalette.cardBackgroundStrong
                                    border.width: 1
                                    border.color: root.themePalette.cardBorder
                                    implicitHeight: 38
                                    implicitWidth: metricLabel.implicitWidth + 28

                                    Text {
                                        id: metricLabel
                                        anchors.centerIn: parent
                                        text: parent.modelData
                                        font.family: bridge.uiFontFamily
                                        font.pixelSize: 12
                                        color: root.themePalette.textSecondary
                                    }
                                }
                            }

                            Item { Layout.fillWidth: true }

                            ActionButton {
                                text: "Stop Listening"
                                tone: "danger"
                                themePalette: root.themePalette
                                uiFontFamily: bridge.uiFontFamily
                                onClicked: bridge.stopListening()
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            OrbCore {
                                anchors.centerIn: parent
                                themePalette: root.themePalette
                                serifFontFamily: bridge.serifFontFamily
                                uiFontFamily: bridge.uiFontFamily
                                statusText: bridge.statusText
                                workflowStepTitle: bridge.workflowStepTitle
                                workflowStepDetail: bridge.workflowStepDetail
                                listening: true
                                workflowRunning: bridge.workflowRunning
                                signalLevel: bridge.signalLevel
                                assistantState: bridge.assistantState
                                immersive: true
                                showLabels: true
                                actionHint: bridge.signalMetrics
                                onToggleRequested: bridge.stopListening()
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            radius: 24
                            color: root.themePalette.cardBackgroundStrong
                            border.width: 1
                            border.color: root.themePalette.cardBorder
                            implicitHeight: listeningInfo.implicitHeight + 26

                            ColumnLayout {
                                id: listeningInfo
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8

                                Text {
                                    text: "Voice Status"
                                    font.family: bridge.serifFontFamily
                                    font.pixelSize: 22
                                    color: root.themePalette.textPrimary
                                }

                                Text {
                                    text: bridge.voiceStatusText
                                    font.family: bridge.uiFontFamily
                                    font.pixelSize: 13
                                    color: root.themePalette.textSecondary
                                }

                                Text {
                                    visible: bridge.lastHeardText.length > 0
                                    text: "Last heard: " + bridge.lastHeardText
                                    wrapMode: Text.Wrap
                                    font.family: bridge.uiFontFamily
                                    font.pixelSize: 12
                                    color: root.themePalette.textMuted
                                }
                            }
                        }
                    }
                }

                Item {
                    id: executingPage

                    RowLayout {
                        anchors.fill: parent
                        spacing: 18

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 32
                            color: root.themePalette.heroSurface
                            border.width: 1
                            border.color: root.themePalette.cardBorder

                            Column {
                                anchors.centerIn: parent
                                spacing: 16

                                OrbCore {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    themePalette: root.themePalette
                                    serifFontFamily: bridge.serifFontFamily
                                    uiFontFamily: bridge.uiFontFamily
                                    statusText: bridge.statusText
                                    workflowStepTitle: bridge.workflowStepTitle
                                    workflowStepDetail: bridge.workflowStepDetail
                                    listening: bridge.listening
                                    workflowRunning: true
                                    signalLevel: bridge.signalLevel
                                    assistantState: bridge.assistantState
                                    immersive: true
                                    showLabels: true
                                    actionHint: bridge.workflowStepDetail
                                    onToggleRequested: bridge.showView("logs")
                                }
                            }
                        }

                        ColumnLayout {
                            Layout.preferredWidth: 430
                            Layout.fillHeight: true
                            spacing: 18

                            Rectangle {
                                Layout.fillWidth: true
                                radius: 26
                                color: root.themePalette.cardBackgroundStrong
                                border.width: 1
                                border.color: root.themePalette.cardBorder
                                implicitHeight: 250

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 20
                                    spacing: 12

                                    Text {
                                        text: "Execution State"
                                        font.family: bridge.serifFontFamily
                                        font.pixelSize: 28
                                        font.weight: Font.DemiBold
                                        color: root.themePalette.textPrimary
                                    }

                                    Text {
                                        text: bridge.workflowStepTitle
                                        font.family: bridge.uiFontFamily
                                        font.pixelSize: 18
                                        font.weight: Font.Medium
                                        color: root.themePalette.textPrimary
                                    }

                                    Text {
                                        text: bridge.workflowStepDetail
                                        wrapMode: Text.Wrap
                                        font.family: bridge.uiFontFamily
                                        font.pixelSize: 13
                                        color: root.themePalette.textSecondary
                                    }

                                    Text {
                                        visible: bridge.lastResponseText.length > 0
                                        text: bridge.lastResponseText
                                        wrapMode: Text.Wrap
                                        font.family: bridge.uiFontFamily
                                        font.pixelSize: 12
                                        color: root.themePalette.textMuted
                                    }
                                }
                            }

                            LogPanel {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                themePalette: root.themePalette
                                serifFontFamily: bridge.serifFontFamily
                                uiFontFamily: bridge.uiFontFamily
                                titleText: "Active Feed"
                                subtitleText: "Live progress, voice state, and execution detail"
                                logModel: logModel
                                compact: true
                            }
                        }
                    }
                }

                SettingsPage {
                    id: settingsPage
                    themePalette: root.themePalette
                    serifFontFamily: bridge.serifFontFamily
                    uiFontFamily: bridge.uiFontFamily
                    configObject: root.workingConfig
                    audioDevices: bridge.audioDevices
                    audioOutputDevices: bridge.audioOutputDevices
                    workflowNames: bridge.workflowNames
                    onSaveRequested: bridge.saveConfig(configObject)
                    onReloadRequested: bridge.reloadConfig()
                    onOpenConfigRequested: bridge.openConfigFolder()
                    onOpenLogsRequested: bridge.openLogsFolder()
                    onTestWorkflowRequested: bridge.testWorkflow(configObject)
                    onCalibrateRequested: bridge.calibrateMicrophone(configObject)
                    onRefreshModelsRequested: bridge.refreshModels(configObject)
                    onTestMicrophoneRequested: bridge.testMicrophone(configObject)
                    onTestSttRequested: bridge.testStt(configObject)
                    onTestTtsRequested: bridge.testTts(configObject)
                    onTestAiRequested: bridge.testAi(configObject)
                }

                Item {
                    id: logsPage

                    RowLayout {
                        anchors.fill: parent
                        spacing: 18

                        LogPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            themePalette: root.themePalette
                            serifFontFamily: bridge.serifFontFamily
                            uiFontFamily: bridge.uiFontFamily
                            titleText: "System Logs"
                            subtitleText: "Timestamps, workflow actions, voice runtime state, warnings, and device status"
                            logModel: logModel
                            compact: false
                        }

                        ColumnLayout {
                            Layout.preferredWidth: 360
                            Layout.fillHeight: true
                            spacing: 18

                            Rectangle {
                                Layout.fillWidth: true
                                radius: 26
                                color: root.themePalette.cardBackgroundStrong
                                border.width: 1
                                border.color: root.themePalette.cardBorder
                                implicitHeight: 240

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    spacing: 10

                                    Text {
                                        text: "Status Summary"
                                        font.family: bridge.serifFontFamily
                                        font.pixelSize: 24
                                        font.weight: Font.DemiBold
                                        color: root.themePalette.textPrimary
                                    }

                                    Text {
                                        text: bridge.statusText
                                        font.family: bridge.uiFontFamily
                                        font.pixelSize: 16
                                        color: root.themePalette.textPrimary
                                    }

                                    Text {
                                        text: bridge.voiceStatusText
                                        wrapMode: Text.Wrap
                                        font.family: bridge.uiFontFamily
                                        font.pixelSize: 12
                                        color: root.themePalette.textSecondary
                                    }

                                    Text {
                                        visible: bridge.lastHeardText.length > 0
                                        text: "Last heard: " + bridge.lastHeardText
                                        wrapMode: Text.Wrap
                                        font.family: bridge.uiFontFamily
                                        font.pixelSize: 12
                                        color: root.themePalette.textMuted
                                    }
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                radius: 26
                                color: root.themePalette.cardBackgroundStrong
                                border.width: 1
                                border.color: root.themePalette.cardBorder

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    spacing: 12

                                    Text {
                                        text: "Quick Actions"
                                        font.family: bridge.serifFontFamily
                                        font.pixelSize: 24
                                        font.weight: Font.DemiBold
                                        color: root.themePalette.textPrimary
                                    }

                                    ActionButton {
                                        Layout.fillWidth: true
                                        text: "Refresh AI Connection"
                                        tone: "secondary"
                                        themePalette: root.themePalette
                                        uiFontFamily: bridge.uiFontFamily
                                        onClicked: bridge.refreshModels(root.workingConfig)
                                    }

                                    ActionButton {
                                        Layout.fillWidth: true
                                        text: "Refresh Audio Devices"
                                        tone: "secondary"
                                        themePalette: root.themePalette
                                        uiFontFamily: bridge.uiFontFamily
                                        onClicked: bridge.refreshAudioDevices()
                                    }

                                    ActionButton {
                                        Layout.fillWidth: true
                                        text: "Open Logs Folder"
                                        tone: "quiet"
                                        themePalette: root.themePalette
                                        uiFontFamily: bridge.uiFontFamily
                                        onClicked: bridge.openLogsFolder()
                                    }

                                    ActionButton {
                                        Layout.fillWidth: true
                                        text: "Open Config Folder"
                                        tone: "quiet"
                                        themePalette: root.themePalette
                                        uiFontFamily: bridge.uiFontFamily
                                        onClicked: bridge.openConfigFolder()
                                    }

                                    ActionButton {
                                        Layout.fillWidth: true
                                        text: "Copy Diagnostics"
                                        tone: "quiet"
                                        themePalette: root.themePalette
                                        uiFontFamily: bridge.uiFontFamily
                                        onClicked: bridge.copyDiagnostics()
                                    }

                                    ActionButton {
                                        Layout.fillWidth: true
                                        text: "Export Chat"
                                        tone: "quiet"
                                        themePalette: root.themePalette
                                        uiFontFamily: bridge.uiFontFamily
                                        onClicked: bridge.exportChat()
                                    }

                                    ActionButton {
                                        Layout.fillWidth: true
                                        text: "Clear Chat"
                                        tone: "quiet"
                                        themePalette: root.themePalette
                                        uiFontFamily: bridge.uiFontFamily
                                        onClicked: bridge.clearChat()
                                    }

                                    ActionButton {
                                        Layout.fillWidth: true
                                        text: "Return Home"
                                        tone: "quiet"
                                        themePalette: root.themePalette
                                        uiFontFamily: bridge.uiFontFamily
                                        onClicked: bridge.showView("home")
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        visible: root.workingConfig.ui && root.workingConfig.ui.show_debug_panel
                                        radius: 18
                                        color: Qt.rgba(1, 1, 1, root.themePalette.name === "dark" ? 0.02 : 0.72)
                                        border.width: 1
                                        border.color: root.themePalette.cardBorder

                                        ScrollView {
                                            anchors.fill: parent
                                            anchors.margins: 10
                                            clip: true

                                            TextArea {
                                                readOnly: true
                                                wrapMode: TextEdit.Wrap
                                                text: bridge.diagnosticsText
                                                font.family: bridge.uiFontFamily
                                                font.pixelSize: 11
                                                color: root.themePalette.textSecondary
                                                background: null
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    SequentialAnimation {
        id: pageFade
        running: false
        NumberAnimation {
            target: pageFrame
            property: "opacity"
            from: 0.0
            to: 1.0
            duration: 240
            easing.type: Easing.OutQuad
        }
    }

    Popup {
        id: toastPopup
        x: root.width - width - 28
        y: 28
        width: 380
        height: toastContent.implicitHeight + 32
        padding: 0
        modal: false
        focus: false
        closePolicy: Popup.NoAutoClose
        background: Rectangle {
            radius: 22
            color: root.themePalette.cardBackgroundStrong
            border.width: 1
            border.color: root.themePalette.cardBorder
        }

        Item {
            anchors.fill: parent

            Column {
                id: toastContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 6

                Text {
                    text: root.toastTitle
                    font.family: bridge.serifFontFamily
                    font.pixelSize: 20
                    color: root.themePalette.textPrimary
                }

                Text {
                    width: parent.width
                    text: root.toastMessage
                    wrapMode: Text.Wrap
                    font.family: bridge.uiFontFamily
                    font.pixelSize: 13
                    color: root.themePalette.textSecondary
                }
            }
        }
    }

    Timer {
        id: toastTimer
        interval: 3600
        repeat: false
        onTriggered: toastPopup.close()
    }
}

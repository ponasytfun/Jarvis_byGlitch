import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root

    property var themePalette
    property string serifFontFamily: "Georgia"
    property string uiFontFamily: "Segoe UI"
    property string statusText: "Idle"
    property string workflowStepTitle: "Awaiting Command"
    property string workflowStepDetail: "The command core is standing by."
    property string assistantState: workflowRunning ? "executing" : (listening ? "listening" : "idle")
    property bool listening: false
    property bool workflowRunning: false
    property real signalLevel: 0.0
    property bool immersive: false
    property bool showLabels: true
    property real sizeFactor: 1.0
    property string actionHint: listening ? "Tap the core to stop listening" : "Tap the core to begin listening"

    readonly property color stateColor: assistantState === "error"
                                        ? themePalette.danger
                                        : assistantState === "executing_action" || assistantState === "executing"
                                        ? themePalette.executingGlow
                                        : assistantState === "speaking"
                                          ? themePalette.speakingGlow
                                          : assistantState === "thinking"
                                            ? themePalette.thinkingGlow
                                            : assistantState === "listening"
                                              ? themePalette.listeningGlow
                                              : themePalette.idleGlow
    readonly property real reactiveBoost: Math.max(0.04, signalLevel)
    readonly property real nucleusSize: (immersive ? 220 : 188) * root.sizeFactor
    readonly property real haloSize: (immersive ? 690 : 560) * root.sizeFactor
    readonly property var shellCapacities: [2, 8, 18, 32, 21, 9, 2]

    signal toggleRequested()

    property real orbitPhase: 0
    property real shellPhase: 0
    property real haloPulse: 1.0
    property real nucleusTwist: 0

    implicitWidth: (immersive ? 760 : 610) * root.sizeFactor
    implicitHeight: (immersive ? 760 : 610) * root.sizeFactor

    function electronShell(index) {
        var offset = 0
        for (var shell = 0; shell < shellCapacities.length; shell++) {
            var capacity = shellCapacities[shell]
            if (index < offset + capacity)
                return shell
            offset += capacity
        }
        return shellCapacities.length - 1
    }

    function shellLocalIndex(index) {
        var offset = 0
        for (var shell = 0; shell < shellCapacities.length; shell++) {
            var capacity = shellCapacities[shell]
            if (index < offset + capacity)
                return index - offset
            offset += capacity
        }
        return 0
    }

    function shellRadiusX(shellIndex) {
        return ((immersive ? 138 : 110) + (shellIndex * 28)) * root.sizeFactor
    }

    function shellRadiusY(shellIndex) {
        return root.shellRadiusX(shellIndex) * (0.58 + ((shellIndex % 3) * 0.09))
    }

    function shellRotation(shellIndex) {
        return (shellIndex * 23) + ((shellIndex % 2 === 0 ? 1 : -1) * root.orbitPhase * 0.08)
    }

    function shellSpeed(shellIndex) {
        var multiplier = assistantState === "error" ? 1.35
                         : assistantState === "executing_action" || assistantState === "executing" ? 1.9
                         : assistantState === "speaking" ? 1.55
                         : assistantState === "thinking" ? 1.45
                         : assistantState === "listening" ? 1.18
                         : 0.8
        return multiplier * (0.65 + (shellIndex * 0.11))
    }

    function electronAngle(index) {
        var shell = electronShell(index)
        var localIndex = shellLocalIndex(index)
        var shellCount = shellCapacities[shell]
        var baseAngle = (360 / Math.max(1, shellCount)) * localIndex
        var drift = root.orbitPhase * shellSpeed(shell)
        return baseAngle + drift + (shell * 17)
    }

    function stateLabel() {
        switch (assistantState) {
        case "speaking":
            return "Speaking"
        case "thinking":
            return "Thinking"
        case "error":
            return "Error"
        case "executing_action":
        case "executing":
            return "Executing"
        case "listening":
            return "Listening"
        default:
            return "Idle"
        }
    }

    NumberAnimation on orbitPhase {
        from: 0
        to: 360
        duration: assistantState === "executing_action" || assistantState === "executing"
                  ? 5200
                  : assistantState === "speaking"
                    ? 6600
                    : assistantState === "thinking"
                      ? 7400
                      : assistantState === "listening"
                        ? 9600
                        : 16200
        loops: Animation.Infinite
    }

    NumberAnimation on shellPhase {
        from: 0
        to: 360
        duration: assistantState === "executing_action" || assistantState === "executing" ? 2800 : 4200
        loops: Animation.Infinite
    }

    NumberAnimation on nucleusTwist {
        from: 0
        to: 360
        duration: assistantState === "executing_action" || assistantState === "executing" ? 8200 : 12600
        loops: Animation.Infinite
    }

    SequentialAnimation on haloPulse {
        loops: Animation.Infinite
        NumberAnimation {
            to: assistantState === "executing_action" || assistantState === "executing"
                ? 1.18
                : assistantState === "error"
                  ? 1.12
                : assistantState === "speaking"
                  ? 1.14
                  : assistantState === "thinking"
                    ? 1.11
                    : assistantState === "listening"
                      ? 1.08
                      : 1.03
            duration: assistantState === "executing_action" || assistantState === "executing" ? 640 : 1280
            easing.type: Easing.InOutQuad
        }
        NumberAnimation {
            to: 0.985
            duration: assistantState === "executing_action" || assistantState === "executing" ? 720 : 1360
            easing.type: Easing.InOutQuad
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: root.haloSize
        height: width
        radius: width / 2
        color: root.stateColor
        opacity: assistantState === "idle" ? 0.055 : (assistantState === "listening" ? 0.1 : 0.16)
        scale: root.haloPulse + (root.reactiveBoost * 0.18)
    }

    Rectangle {
        anchors.centerIn: parent
        width: root.haloSize * 0.82
        height: width
        radius: width / 2
        color: themePalette.atomBackdrop
        opacity: themePalette.name === "dark" ? 0.36 : 0.22
        scale: 0.96 + (root.reactiveBoost * 0.08)
    }

    Repeater {
        model: 7

        delegate: Rectangle {
            required property int index

            width: root.shellRadiusX(index) * 2
            height: root.shellRadiusY(index) * 2
            radius: width / 2
            anchors.centerIn: parent
            color: "transparent"
            border.width: 1
            border.color: index % 2 === 0 ? root.themePalette.atomOrbit : root.themePalette.accentSecondary
            opacity: assistantState === "idle" ? 0.17 : 0.34
            rotation: root.shellRotation(index)
        }
    }

    Repeater {
        model: 92

        delegate: Rectangle {
            required property int index

            readonly property int shellIndex: root.electronShell(index)
            readonly property real angleDeg: root.electronAngle(index)
            readonly property real angleRad: angleDeg * Math.PI / 180
            readonly property real radiusX: root.shellRadiusX(shellIndex)
            readonly property real radiusY: root.shellRadiusY(shellIndex)
            readonly property real localSize: ((shellIndex % 3 === 0) ? 6.4 : 5.1) * root.sizeFactor

            width: localSize
            height: localSize
            radius: width / 2
            color: index % 5 === 0 ? root.themePalette.atomElectronAlt : root.themePalette.atomElectron
            opacity: assistantState === "idle" ? 0.62 : 0.92
            scale: 0.96 + (root.reactiveBoost * 0.14)
            x: root.width / 2 + Math.cos(angleRad) * radiusX - width / 2
            y: root.height / 2 + Math.sin(angleRad) * radiusY - height / 2

            Rectangle {
                anchors.centerIn: parent
                width: parent.width * 2.8
                height: width
                radius: width / 2
                color: parent.color
                opacity: 0.18
            }
        }
    }

    Rectangle {
        id: nucleusHalo
        anchors.centerIn: parent
        width: root.nucleusSize * 1.38
        height: width
        radius: width / 2
        color: root.stateColor
        opacity: assistantState === "idle" ? 0.11 : 0.21
        scale: root.haloPulse + (root.reactiveBoost * 0.05)
    }

    Rectangle {
        id: nucleusField
        anchors.centerIn: parent
        width: root.nucleusSize
        height: width
        radius: width / 2
        color: root.themePalette.atomCoreGlass
        border.width: 1
        border.color: Qt.lighter(root.stateColor, 1.25)
        scale: 1.0 + (root.reactiveBoost * 0.05)

        Repeater {
            model: 235

            delegate: Rectangle {
                required property int index

                readonly property bool proton: index < 92
                readonly property real goldenAngle: 2.399963229728653
                readonly property real radiusFactor: Math.sqrt((index + 0.7) / 235)
                readonly property real localAngle: (index * goldenAngle) + (root.nucleusTwist * Math.PI / 180)
                readonly property real nucleusRadius: (nucleusField.width * 0.42) * radiusFactor
                readonly property real jitter: Math.sin((root.shellPhase + (index * 4)) * Math.PI / 180) * (root.reactiveBoost * 1.9)
                readonly property real particleSize: proton ? 9.2 * root.sizeFactor : 8.0 * root.sizeFactor

                width: particleSize
                height: particleSize
                radius: width / 2
                color: proton ? root.themePalette.atomProton : root.themePalette.atomNeutron
                opacity: proton ? 0.84 : 0.72
                x: nucleusField.width / 2 + Math.cos(localAngle) * (nucleusRadius + jitter) - width / 2
                y: nucleusField.height / 2 + Math.sin(localAngle) * (nucleusRadius + jitter) - height / 2

                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width * 1.9
                    height: width
                    radius: width / 2
                    color: parent.color
                    opacity: 0.16
                }
            }
        }

        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.3
            height: width
            radius: width / 2
            color: "#FFFFFF"
            opacity: assistantState === "idle" ? 0.07 : 0.11
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.toggleRequested()
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: root.nucleusSize * 2.1
        height: width
            radius: width / 2
            color: "transparent"
            border.width: 1
            border.color: root.stateColor
        opacity: assistantState === "idle" ? 0.18 : 0.28
        rotation: -root.orbitPhase * 0.22
    }

    Column {
        visible: root.showLabels
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: nucleusField.bottom
        anchors.topMargin: (root.immersive ? 26 : 24) * root.sizeFactor
        spacing: 6

        Text {
            text: root.stateLabel()
            font.family: root.serifFontFamily
            font.pixelSize: Math.round((root.immersive ? 42 : 34) * root.sizeFactor)
            font.weight: Font.DemiBold
            color: root.themePalette.textPrimary
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            text: "U-235 core | 92p | 143n | 92e"
            font.family: root.uiFontFamily
            font.pixelSize: Math.round(13 * root.sizeFactor)
            font.weight: Font.Medium
            color: root.themePalette.textSecondary
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            text: root.workflowStepTitle
            font.family: root.uiFontFamily
            font.pixelSize: Math.round(14 * root.sizeFactor)
            font.weight: Font.Medium
            color: root.themePalette.textSecondary
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            text: root.actionHint
            font.family: root.uiFontFamily
            font.pixelSize: Math.round(12 * root.sizeFactor)
            color: root.themePalette.textMuted
            horizontalAlignment: Text.AlignHCenter
        }
    }
}

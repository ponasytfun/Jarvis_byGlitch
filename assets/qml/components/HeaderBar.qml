import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "."

Rectangle {
    id: root

    property var themePalette
    property string titleText: "JarvisAssistant"
    property string subtitleText: "Local desktop command core"
    property string themeName: "dark"
    property string currentView: "home"
    property string serifFontFamily: "Georgia"
    property string uiFontFamily: "Segoe UI"

    signal navigateRequested(string viewName)
    signal testRequested()
    signal advancedRequested()
    signal openLogsRequested()
    signal darkThemeRequested()
    signal lightThemeRequested()

    radius: 26
    color: root.themePalette.cardBackgroundStrong
    border.width: 1
    border.color: root.themePalette.cardBorder

    RowLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 18

        ColumnLayout {
            Layout.preferredWidth: 248
            spacing: 1

            Text {
                text: root.titleText
                font.family: root.serifFontFamily
                font.pixelSize: 28
                font.weight: Font.DemiBold
                color: root.themePalette.textPrimary
            }

            Text {
                text: root.subtitleText
                font.family: root.uiFontFamily
                font.pixelSize: 12
                color: root.themePalette.textSecondary
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            radius: 24
            color: root.themePalette.buttonQuietFill
            border.width: 1
            border.color: root.themePalette.cardBorder

            RowLayout {
                anchors.fill: parent
                anchors.margins: 5
                spacing: 6

                Repeater {
                    model: [
                        { "label": "Home", "view": "home" },
                        { "label": "Listening", "view": "listening" },
                        { "label": "Executing", "view": "executing" },
                        { "label": "Settings", "view": "settings" },
                        { "label": "Logs", "view": "logs" }
                    ]

                    delegate: Button {
                        required property var modelData

                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        text: modelData.label
                        hoverEnabled: true
                        onClicked: root.navigateRequested(modelData.view)

                        background: Rectangle {
                            radius: 19
                            color: root.currentView === parent.modelData.view ? root.themePalette.buttonPrimaryFill : "transparent"
                            border.width: 1
                            border.color: root.currentView === parent.modelData.view ? root.themePalette.accentSoft : "transparent"
                        }

                        contentItem: Text {
                            text: parent.text
                            color: root.currentView === parent.modelData.view ? root.themePalette.textPrimary : root.themePalette.textSecondary
                            font.family: root.uiFontFamily
                            font.pixelSize: 12
                            font.weight: Font.Medium
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }
        }

        ActionButton {
            text: "Test Workflow"
            tone: "secondary"
            themePalette: root.themePalette
            uiFontFamily: root.uiFontFamily
            onClicked: root.testRequested()
        }

        ActionButton {
            text: "Advanced Settings"
            tone: "quiet"
            themePalette: root.themePalette
            uiFontFamily: root.uiFontFamily
            onClicked: root.advancedRequested()
        }

        ActionButton {
            text: "Logs"
            tone: "quiet"
            themePalette: root.themePalette
            uiFontFamily: root.uiFontFamily
            onClicked: root.openLogsRequested()
        }

        ThemeToggle {
            Layout.preferredWidth: 170
            Layout.preferredHeight: 44
            themePalette: root.themePalette
            themeName: root.themeName
            uiFontFamily: root.uiFontFamily
            onDarkRequested: root.darkThemeRequested()
            onLightRequested: root.lightThemeRequested()
        }
    }
}

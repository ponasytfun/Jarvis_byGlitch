import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var themePalette
    property string uiFontFamily: "Segoe UI"
    property string serifFontFamily: "Georgia"
    property string titleText: "Execution Feed"
    property string subtitleText: "Live workflow logs"
    property var logModel
    property bool compact: false

    radius: 26
    color: root.themePalette.cardBackgroundStrong
    border.width: 1
    border.color: root.themePalette.cardBorder

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.compact ? 14 : 18
        spacing: root.compact ? 10 : 14

        RowLayout {
            Layout.fillWidth: true

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    text: root.titleText
                    font.family: root.serifFontFamily
                    font.pixelSize: root.compact ? 18 : 22
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
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            radius: 22
            color: Qt.rgba(0, 0, 0, root.themePalette.name === "dark" ? 0.16 : 0.035)
            border.width: 1
            border.color: root.themePalette.line

            ListView {
                id: logList
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8
                clip: true
                model: root.logModel

                delegate: Rectangle {
                    id: logDelegate
                    required property string text
                    width: ListView.view.width
                    radius: 16
                    color: Qt.rgba(1, 1, 1, root.themePalette.name === "dark" ? 0.025 : 0.55)
                    border.width: 1
                    border.color: root.themePalette.cardBorder
                    implicitHeight: logText.implicitHeight + 18

                    Text {
                        id: logText
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        anchors.verticalCenter: parent.verticalCenter
                        text: logDelegate.text
                        wrapMode: Text.Wrap
                        font.family: root.uiFontFamily
                        font.pixelSize: root.compact ? 11 : 12
                        lineHeight: 1.25
                        color: root.themePalette.textSecondary
                    }
                }

                onCountChanged: positionViewAtEnd()
            }
        }
    }
}

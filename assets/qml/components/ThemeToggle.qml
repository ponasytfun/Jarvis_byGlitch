import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root

    property var themePalette
    property string themeName: "dark"
    property string uiFontFamily: "Segoe UI"

    signal darkRequested()
    signal lightRequested()

    radius: 22
    color: root.themePalette.buttonQuietFill
    border.width: 1
    border.color: root.themePalette.cardBorder

    RowLayout {
        anchors.fill: parent
        anchors.margins: 4
        spacing: 4

        Repeater {
            model: [
                { "label": "Dark", "value": "dark" },
                { "label": "Light", "value": "light" }
            ]

            delegate: Button {
                required property var modelData

                Layout.preferredWidth: 78
                Layout.preferredHeight: 34
                text: modelData.label
                hoverEnabled: true
                onClicked: {
                    if (modelData.value === "dark")
                        root.darkRequested()
                    else
                        root.lightRequested()
                }

                background: Rectangle {
                    radius: 17
                    color: root.themeName === parent.modelData.value ? root.themePalette.buttonPrimaryFill : "transparent"
                    border.width: 1
                    border.color: root.themeName === parent.modelData.value ? root.themePalette.accentSoft : "transparent"
                }

                contentItem: Text {
                    text: parent.text
                    color: root.themeName === parent.modelData.value ? root.themePalette.textPrimary : root.themePalette.textSecondary
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

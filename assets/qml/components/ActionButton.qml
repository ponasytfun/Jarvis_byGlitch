import QtQuick 2.15
import QtQuick.Controls 2.15

Button {
    id: root

    property var themePalette
    property string tone: "secondary"
    property string uiFontFamily: "Segoe UI"

    implicitHeight: 46
    implicitWidth: 152
    padding: 0
    font.family: root.uiFontFamily
    hoverEnabled: true

    background: Rectangle {
        radius: 23
        border.width: 1
        border.color: {
            if (root.tone === "primary")
                return root.themePalette.accent
            if (root.tone === "danger")
                return root.themePalette.danger
            return root.hovered ? root.themePalette.accentSoft : root.themePalette.cardBorder
        }
        color: {
            if (root.tone === "primary")
                return root.down ? root.themePalette.accent : root.themePalette.buttonPrimaryFill
            if (root.tone === "danger")
                return root.down ? Qt.darker(root.themePalette.danger, 1.15) : Qt.rgba(1, 0.35, 0.35, root.themePalette.name === "dark" ? 0.13 : 0.18)
            if (root.tone === "quiet")
                return root.down ? root.themePalette.buttonSecondaryFill : root.themePalette.buttonQuietFill
            return root.down ? root.themePalette.buttonPrimaryFill : root.themePalette.buttonSecondaryFill
        }
        opacity: root.enabled ? 1.0 : 0.45
    }

    contentItem: Text {
        text: root.text
        color: {
            if (root.tone === "primary")
                return root.themePalette.buttonPrimaryText
            if (root.tone === "danger")
                return root.themePalette.textPrimary
            return root.themePalette.textPrimary
        }
        font.family: root.uiFontFamily
        font.pixelSize: 13
        font.weight: Font.Medium
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}

// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    required property var studio
    property string message: ""
    property string acceptText: ""
    parent: Overlay.overlay
    popupType: Popup.Item
    anchors.centerIn: parent
    width: Math.min(440,studio.width-48)
    modal: true; focus: true; padding: 20
    closePolicy: Popup.CloseOnEscape
    standardButtons: Dialog.NoButton
    font: studio.font
    background: Rectangle { radius: 14; color: studio.panel; border.color: studio.edge }
    Overlay.modal: Rectangle { color: studio.lightTheme ? "#66243139" : "#88000000" }
    header: Label {
        text: dialog.title; textFormat: Text.PlainText; color: studio.ink
        font.family: studio.font.family; font.pixelSize: 19
        leftPadding: 20; rightPadding: 20; topPadding: 20; bottomPadding: 0
        wrapMode: Text.WordWrap
    }
    contentItem: Label {
        text: dialog.message; textFormat: Text.PlainText; color: studio.muted
        font: studio.font; wrapMode: Text.WordWrap
    }
    footer: Item {
        implicitHeight: 68
        RowLayout {
            anchors.right: parent.right; anchors.rightMargin: 20
            anchors.bottom: parent.bottom; anchors.bottomMargin: 18; spacing: 10
            Button {
                objectName: "confirmationCancel"
                text: studio.tr("Cancel"); implicitHeight: 36; leftPadding: 16; rightPadding: 16
                contentItem: Label { text: parent.text; textFormat: Text.PlainText; color: studio.ink; font: studio.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { radius: 8; color: parent.hovered ? studio.hoverColor : studio.controlColor; border.color: parent.activeFocus ? studio.accent : studio.edge }
                onClicked: dialog.reject()
            }
            Button {
                objectName: "confirmationAccept"
                text: dialog.acceptText; implicitHeight: 36; leftPadding: 16; rightPadding: 16
                contentItem: Label { text: parent.text; textFormat: Text.PlainText; color: "#08271e"; font: studio.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { radius: 8; color: studio.primaryFill; border.color: parent.activeFocus ? studio.ink : studio.primaryFill }
                onClicked: dialog.accept()
            }
        }
    }
}

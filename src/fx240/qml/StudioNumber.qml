// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls

SpinBox {
    id: control
    required property var studio
    implicitHeight: 34; implicitWidth: 120
    padding: 4; leftPadding: 34; rightPadding: 34
    background: Rectangle { radius: 7; color: studio.controlColor; border.color: control.activeFocus ? studio.accent : studio.edge; opacity: control.enabled ? 1 : .5 }
    contentItem: TextInput {
        text: control.textFromValue(control.value,control.locale)
        font: control.font; color: studio.ink; selectionColor: studio.selection; selectedTextColor: studio.ink
        horizontalAlignment: Qt.AlignHCenter; verticalAlignment: Qt.AlignVCenter
        readOnly: !control.editable; validator: control.validator
        inputMethodHints: Qt.ImhFormattedNumbersOnly
        opacity: control.enabled ? 1 : .5
    }
    up.indicator: Rectangle {
        x: control.width-width; height: control.height; width: 32; radius: 7
        color: control.up.pressed ? studio.selection : control.up.hovered ? studio.hoverColor : "transparent"
        Text { anchors.centerIn: parent; text: "+"; color: studio.ink; font.pixelSize: 20; opacity: control.up.enabled ? 1 : .35 }
    }
    down.indicator: Rectangle {
        height: control.height; width: 32; radius: 7
        color: control.down.pressed ? studio.selection : control.down.hovered ? studio.hoverColor : "transparent"
        Text { anchors.centerIn: parent; text: "−"; color: studio.ink; font.pixelSize: 20; opacity: control.down.enabled ? 1 : .35 }
    }
}

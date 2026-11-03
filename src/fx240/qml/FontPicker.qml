// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Button {
    id: picker
    required property var studio
    property var model: []
    property int currentIndex: 0
    readonly property string currentText: model[currentIndex] || ""
    property string displayText: currentText
    signal activated(int index)
    implicitHeight: 34; implicitWidth: 120; Layout.minimumWidth: 0
    Accessible.name: studio.tr("Installed fonts")
    onClicked: popup.open()
    contentItem: Text { text: picker.displayText; textFormat: Text.PlainText; color: studio.ink; font: picker.font; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight; rightPadding: 22 }
    background: Rectangle { radius: 7; color: picker.hovered ? studio.hoverColor : studio.controlColor; border.color: picker.activeFocus ? studio.accent : studio.edge }
    Text { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: "⌄"; color: studio.muted }
    Popup {
        id: popup; objectName: "fontSearchPopup"; popupType: Popup.Item
        parent: Overlay.overlay
        width: Math.min(400,picker.studio.width-40); height: Math.min(340,picker.studio.height-40); padding: 12; focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        function positionNearAnchor() {
            var position=picker.mapToItem(parent,0,picker.height)
            x=Math.max(12,Math.min(position.x,picker.studio.width-width-12))
            y=Math.max(12,Math.min(position.y+6,picker.studio.height-height-12))
        }
        onOpened: { positionNearAnchor(); search.text=""; search.forceActiveFocus() }
        Connections {
            target: picker.studio
            function onWidthChanged() { if(popup.visible) popup.positionNearAnchor() }
            function onHeightChanged() { if(popup.visible) popup.positionNearAnchor() }
        }
        background: Rectangle { color: studio.panel; border.color: studio.edge; radius: 12 }
        contentItem: ColumnLayout {
            spacing: 10
            TextField {
                id: search; objectName: "fontSearchField"; Layout.fillWidth: true; implicitHeight: 36
                placeholderText: studio.tr("Search fonts…"); color: studio.ink; placeholderTextColor: studio.muted
                selectByMouse: true; maximumLength: 128
                background: Rectangle { radius: 7; color: studio.controlColor; border.color: search.activeFocus ? studio.accent : studio.edge }
                Keys.onDownPressed: { results.forceActiveFocus(); results.currentIndex=0 }
                onAccepted: { if (results.count>0) results.choose(results.currentIndex<0 ? 0 : results.currentIndex) }
            }
            ListView {
                id: results; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 3
                model: {
                    var items=[]; var query=search.text.toLocaleLowerCase()
                    for (var i=0;i<picker.model.length;i++) {
                        if (!query || picker.model[i].toLocaleLowerCase().indexOf(query)>=0) items.push({label:picker.model[i], original:i})
                    }
                    return items
                }
                function choose(index) { if(index<0 || index>=count) return; var original=model[index].original; picker.currentIndex=original; picker.activated(original); popup.close() }
                Keys.onReturnPressed: choose(currentIndex)
                delegate: ItemDelegate {
                    required property var modelData; required property int index
                    width: results.width; height: 38; highlighted: results.currentIndex===index
                    contentItem: Text { text: parent.modelData.label; textFormat: Text.PlainText; color: studio.ink; font: picker.font; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                    background: Rectangle { radius: 6; color: parent.highlighted ? studio.selection : parent.hovered ? studio.hoverColor : "transparent" }
                    onClicked: results.choose(index)
                }
                ScrollBar.vertical: ScrollBar {
                    contentItem: Rectangle { implicitWidth: 6; radius: 3; color: studio.muted; opacity: .5 }
                    background: Rectangle { color: "transparent" }
                }
                Text { anchors.centerIn: parent; visible: results.count===0; text: studio.tr("No matching fonts"); color: studio.muted }
            }
        }
    }
}

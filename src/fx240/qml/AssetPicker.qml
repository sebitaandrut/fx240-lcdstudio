// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Fx240 1.0

Dialog {
    id: picker
    required property var studio
    property string kind: "image"
    property string initialPath: ""
    signal selected(url file)
    objectName: "assetPicker"
    parent: Overlay.overlay; popupType: Popup.Item; anchors.centerIn: parent
    width: Math.min(900,studio.width-48); height: Math.min(600,studio.height-64)
    modal: true; focus: true; padding: 20; closePolicy: Popup.CloseOnEscape
    title: studio.tr(kind==="font" ? "Choose a font" : "Choose a background")
    onAboutToShow: { search.text=""; browser.open(kind,initialPath) }
    onClosed: browser.cancel()
    LocalFileBrowser {
        id: browser; objectName: "assetBrowser"
        onChosen: function(file) { picker.selected(file); picker.close() }
    }
    component Copy: Label { textFormat: Text.PlainText; color: studio.ink; font: studio.font; elide: Text.ElideRight }
    component Tool: Button {
        property bool primary: false
        implicitHeight: 34; leftPadding: 14; rightPadding: 14
        contentItem: Copy { text: parent.text; color: parent.primary ? "#08271e" : studio.ink; opacity: parent.enabled ? 1 : .4; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { radius: 8; color: parent.primary ? studio.primaryFill : parent.hovered ? studio.hoverColor : studio.controlColor; border.color: parent.activeFocus ? studio.accent : studio.edge; opacity: parent.enabled ? 1 : .5 }
    }
    component Entry: TextField {
        color: studio.ink; placeholderTextColor: studio.muted; implicitHeight: 36; font: studio.font; selectByMouse: true
        background: Rectangle { radius: 8; color: studio.controlColor; border.color: parent.activeFocus ? studio.accent : studio.edge }
    }
    background: Rectangle { radius: 14; color: studio.panel; border.color: studio.edge }
    Overlay.modal: Rectangle { color: studio.lightTheme ? "#66243139" : "#88000000" }
    header: Copy { text: picker.title; font.pixelSize: 20; leftPadding: 20; rightPadding: 20; topPadding: 20; bottomPadding: 4 }
    contentItem: ColumnLayout {
        spacing: 12
        RowLayout {
            Layout.fillWidth: true; spacing: 8
            Tool { text: "↑"; Accessible.name: studio.tr("Parent folder"); onClicked: browser.up() }
            Entry { id: folderField; objectName: "assetFolderPath"; text: browser.folder; maximumLength: 4096; Layout.fillWidth: true; Layout.minimumWidth: 0; onAccepted: browser.go(text); Accessible.name: studio.tr("Folder path") }
            Tool { text: studio.tr("Go"); onClicked: browser.go(folderField.text) }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            Rectangle {
                Layout.preferredWidth: 156; Layout.fillHeight: true; radius: 10; color: studio.backgroundColor; border.color: studio.edge
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 8; spacing: 6
                    Repeater {
                        model: browser.locations
                        delegate: Button {
                            required property var modelData
                            objectName: "assetShortcut-"+modelData.label
                            Layout.fillWidth: true; implicitHeight: 40; leftPadding: 10; rightPadding: 10
                            contentItem: Copy { text: studio.tr(parent.modelData.label); verticalAlignment: Text.AlignVCenter }
                            background: Rectangle { radius: 7; color: browser.folder===parent.modelData.path ? studio.selection : parent.hovered ? studio.hoverColor : "transparent" }
                            onClicked: browser.go(modelData.path)
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8
                Entry { id: search; objectName: "assetSearch"; placeholderText: studio.tr("Search in this folder…"); maximumLength: 128; Layout.fillWidth: true; onTextChanged: browser.clearSelection() }
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; radius: 10; color: studio.backgroundColor; border.color: studio.edge
                    ListView {
                        id: files; objectName: "assetFiles"
                        anchors.fill: parent; anchors.margins: 8; clip: true; spacing: 3
                        model: {
                            var values=[]; var query=search.text.toLocaleLowerCase(); var entries=browser.entries
                            for (var i=0;i<entries.length;i++) if (!query || entries[i].name.toLocaleLowerCase().indexOf(query)>=0) values.push({entry:entries[i],original:i})
                            return values
                        }
                        onCurrentIndexChanged: { if(currentIndex>=0 && currentIndex<count) browser.select(model[currentIndex].original) }
                        Keys.onReturnPressed: { if(currentIndex>=0 && currentIndex<count) browser.activate(model[currentIndex].original) }
                        delegate: ItemDelegate {
                            required property var modelData; required property int index
                            width: files.width-12; height: 40
                            highlighted: browser.selectedIndex===modelData.original
                            background: Rectangle { radius: 7; color: parent.highlighted ? studio.selection : parent.hovered ? studio.hoverColor : "transparent" }
                            contentItem: RowLayout {
                                spacing: 10
                                Image { source: "../assets/icons/"+(studio.lightTheme ? "light/" : "dark/")+(parent.parent.modelData.entry.folder ? "folder-open-muted.svg" : picker.kind==="font" ? "settings-2-muted.svg" : "image-muted.svg"); sourceSize.width: 18; sourceSize.height: 18; Layout.preferredWidth: 18; Layout.preferredHeight: 18 }
                                Copy { text: parent.parent.modelData.entry.name; Layout.fillWidth: true; Layout.minimumWidth: 0; verticalAlignment: Text.AlignVCenter }
                            }
                            onClicked: { files.currentIndex=index; browser.select(modelData.original) }
                            onDoubleClicked: browser.activate(modelData.original)
                        }
                        ScrollBar.vertical: ScrollBar {
                            policy: files.contentHeight>files.height ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                            contentItem: Rectangle { implicitWidth: 6; radius: 3; color: studio.muted; opacity: .5 }
                            background: Rectangle { color: "transparent" }
                        }
                        Copy { anchors.centerIn: parent; width: parent.width-24; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: studio.muted; visible: files.count===0; text: studio.tr(browser.busy ? "Reading folder…" : search.text ? "No matching files" : "No supported files in this folder") }
                    }
                }
            }
        }
        Copy { text: studio.tr(browser.notice); visible: text.length>0; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: studio.muted }
    }
    footer: Item {
        implicitHeight: 68
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 20; anchors.rightMargin: 20; anchors.topMargin: 8; anchors.bottomMargin: 18; spacing: 10
            Copy { text: browser.selectedName || studio.tr(picker.kind==="font" ? "Font files · TTF, OTF" : "Images and GIFs"); Layout.fillWidth: true; Layout.minimumWidth: 0; color: studio.muted }
            Tool { text: studio.tr("Cancel"); onClicked: picker.reject() }
            Tool { objectName: "assetOpen"; text: studio.tr("Open"); primary: true; enabled: browser.canOpen; onClicked: browser.activate(browser.selectedIndex) }
        }
    }
}

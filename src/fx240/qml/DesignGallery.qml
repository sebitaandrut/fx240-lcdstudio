// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: gallery
    required property var studio
    readonly property bool original: bridge.activeContentIndex < bridge.builtinDesignCount
    readonly property int columns: libraryScroll.availableWidth >= 720 ? 4 : 2
    readonly property int thumbnailSize: columns === 4
        ? Math.min(170, Math.max(126, Math.round(libraryScroll.availableWidth / 8.5))) : 102
    property bool managing: false
    property var selectedProfiles: []
    property bool deletionFailed: false
    spacing: 14

    Component.onCompleted: bridge.setGalleryVisible(visible)
    onVisibleChanged: {
        bridge.setGalleryVisible(visible)
        if (!visible) finishManaging()
    }
    function finishManaging() {
        managing = false
        selectedProfiles = []
        deletionFailed = false
    }
    function toggleProfile(identifier) {
        if (selectedProfiles.includes(identifier))
            selectedProfiles = selectedProfiles.filter(id => id !== identifier)
        else
            selectedProfiles = selectedProfiles.concat([identifier])
        deletionFailed = false
    }
    function tr(text) { return studio.tr(text) }

    StudioConfirm {
        id: deleteDesigns
        objectName: "deleteDesignsConfirmation"
        studio: gallery.studio
        title: gallery.tr("Delete selected designs?")
        message: gallery.tr("The selected profiles will be removed from the library. Their images and fonts will stay on this computer.")
        acceptText: gallery.tr("Delete")
        onAccepted: {
            if (bridge.workspace.deleteProfiles(gallery.selectedProfiles)) gallery.finishManaging()
            else gallery.deletionFailed = true
        }
    }

    component Heading: Label {
        font.pixelSize: 19; color: studio.ink; textFormat: Text.PlainText
    }
    component Note: Label {
        color: studio.muted; textFormat: Text.PlainText; wrapMode: Text.Wrap
    }
    component ActionButton: Button {
        id: action
        implicitHeight: 34
        contentItem: Label {
            text: action.text; color: studio.ink
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            opacity: action.enabled ? 1 : .65
        }
        background: Rectangle {
            radius: 8; border.color: action.visualFocus ? studio.accent : studio.edge
            color: action.hovered ? studio.hoverColor : studio.controlColor
        }
    }
    component DesignTile: Button {
        id: tile
        required property int designIndex
        property string profileId: ""
        readonly property bool activeDesign: designIndex === bridge.activeContentIndex
        readonly property bool choosing: gallery.managing && profileId !== ""
        readonly property bool marked: gallery.selectedProfiles.includes(profileId)
        readonly property bool tileSelected: choosing ? marked : activeDesign
        Layout.fillWidth: true; Layout.minimumWidth: 0
        implicitHeight: gallery.thumbnailSize + 38
        checkable: choosing
        checked: marked
        Accessible.name: text + (activeDesign ? " · " + gallery.tr("In use") : "")
        background: Rectangle {
            radius: 10
            color: tile.tileSelected ? studio.selection : tile.hovered ? studio.hoverColor : studio.panel
            border.color: tile.tileSelected || tile.visualFocus ? studio.accent : studio.edge
        }
        contentItem: ColumnLayout {
            spacing: 7
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                implicitWidth: gallery.thumbnailSize; implicitHeight: width; radius: width/2; color: "#090d11"
                Image {
                    id: thumbnail
                    objectName: "designThumbnail-" + tile.designIndex
                    anchors.fill: parent
                    source: bridge.thumbnails.urls[tile.designIndex] || ""
                    smooth: true; cache: false
                }
                Image {
                    visible: thumbnail.status !== Image.Ready
                    anchors.centerIn: parent; width: 26; height: 26
                    source: "../assets/icons/dark/image-muted.svg"
                }
            }
            Label {
                Layout.fillWidth: true; text: tile.text; elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter; textFormat: Text.PlainText
                color: tile.tileSelected ? studio.accent : studio.ink
            }
        }
        Rectangle {
            visible: tile.choosing
            anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 10
            width: 20; height: 20; radius: 5
            color: tile.marked ? studio.primaryFill : studio.controlColor
            border.color: tile.marked ? studio.accent : studio.muted
            Label { anchors.centerIn: parent; visible: tile.marked; text: "✓"; color: "#08271e" }
        }
        onClicked: {
            if (choosing) gallery.toggleProfile(profileId)
            else bridge.selectContent(designIndex)
        }
    }

    ScrollView {
        id: libraryScroll
        Layout.fillHeight: true; Layout.fillWidth: true; Layout.preferredWidth: 500
        clip: true; contentWidth: availableWidth; rightPadding: 10
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ColumnLayout {
            width: libraryScroll.availableWidth
            spacing: 12
            Heading { text: gallery.tr("Originals") }
            GridLayout {
                objectName: "builtinDesignGrid"
                columns: gallery.columns; uniformCellWidths: true
                Layout.fillWidth: true; columnSpacing: 10; rowSpacing: 10
                Repeater {
                    model: bridge.contentLabels.slice(0, bridge.builtinDesignCount)
                    delegate: DesignTile {
                        required property int index
                        required property string modelData
                        objectName: "designTile-" + designIndex
                        designIndex: index; text: modelData
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Heading { text: gallery.tr("My designs") }
                ActionButton {
                    objectName: "manageDesignsButton"; visible: savedGrid.count > 0
                    text: gallery.tr(gallery.managing ? "Cancel" : "Select")
                    onClicked: {
                        if (gallery.managing) gallery.finishManaging()
                        else gallery.managing = true
                    }
                }
                ActionButton {
                    objectName: "newDesignButton"; text: gallery.tr("New design"); visible: !gallery.managing
                    onClicked: { studio.page = 4; bridge.workspace.requestNew() }
                }
                ActionButton {
                    objectName: "deleteSelectedDesignsButton"; visible: gallery.managing
                    text: gallery.tr("Delete selected")
                    enabled: gallery.selectedProfiles.length > 0 && !gallery.selectedProfiles.includes(bridge.activeProfileId)
                    onClicked: deleteDesigns.open()
                }
                Item { Layout.fillWidth: true }
            }
            Note {
                visible: gallery.managing && gallery.selectedProfiles.includes(bridge.activeProfileId)
                text: gallery.tr("Activate another design before deleting the one in use")
                Layout.fillWidth: true
            }
            Note {
                visible: gallery.deletionFailed; text: bridge.workspace.notice
                color: studio.errorColor; Layout.fillWidth: true
            }
            Note { visible: savedGrid.count === 0; text: gallery.tr("Saved designs appear here."); Layout.fillWidth: true }
            GridLayout {
                columns: gallery.columns; uniformCellWidths: true
                Layout.fillWidth: true; columnSpacing: 10; rowSpacing: 10
                Repeater {
                    id: savedGrid
                    model: bridge.contentLabels.slice(bridge.builtinDesignCount)
                    delegate: DesignTile {
                        required property int index
                        required property string modelData
                        objectName: "designTile-" + designIndex
                        designIndex: index + bridge.builtinDesignCount; text: modelData
                        profileId: bridge.profileIds[index] || ""
                    }
                }
                Repeater {
                    model: savedGrid.count ? (gallery.columns - savedGrid.count % gallery.columns) % gallery.columns : 0
                    delegate: Item { Layout.fillWidth: true }
                }
            }
            ActionButton { visible: bridge.workspace.dirty; text: gallery.tr("Continue draft"); onClicked: studio.page = 4 }
            Note { text: bridge.profileNotice; visible: text.length > 0; Layout.fillWidth: true }
        }
    }

    Rectangle {
        objectName: "designPreviewPanel"
        Layout.alignment: Qt.AlignTop
        Layout.fillWidth: true; Layout.preferredWidth: 430
        Layout.maximumWidth: 720
        Layout.preferredHeight: Math.min(720, gallery.height)
        radius: 16; color: studio.panel; border.color: studio.edge
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 18; spacing: 12
            RowLayout {
                Layout.fillWidth: true
                Heading { text: gallery.tr("Preview"); color: studio.accent }
                Item { Layout.fillWidth: true }
                Note { text: "240 × 240" }
            }
            RowLayout {
                Layout.alignment: Qt.AlignHCenter; Layout.maximumWidth: parent.width
                Heading { text: bridge.activeContentName; elide: Text.ElideRight; Layout.minimumWidth: 0; Layout.fillWidth: true }
                Note { text: gallery.tr(gallery.original ? "Original" : "Saved design") }
            }
            Item {
                id: previewStage
                Layout.fillWidth: true; Layout.fillHeight: true
                ColumnLayout {
                    anchors.centerIn: parent; spacing: 12
                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: Math.min(560, previewStage.width,
                                                       previewStage.height - editButton.implicitHeight - 12)
                        Layout.preferredHeight: Layout.preferredWidth
                        color: "#090d11"; radius: width / 2
                        Image {
                            objectName: "framePreview"; anchors.fill: parent
                            source: bridge.previewUrl
                            retainWhileLoading: true; cache: false; smooth: true
                        }
                    }
                    ActionButton {
                        id: editButton
                        Layout.alignment: Qt.AlignHCenter
                        objectName: "openEditorButton"
                        text: gallery.tr(gallery.original ? "Edit copy" : "Edit design")
                        onClicked: { studio.page = 4; bridge.editActive() }
                    }
                }
            }
        }
    }
}

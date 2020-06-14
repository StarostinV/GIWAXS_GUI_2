# -*- coding: utf-8 -*-

from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QMenu, QWidgetAction, QLineEdit

from ...app.app import App
from ...app.rois.roi import Roi, RoiTypes


class AbstractRoiContextMenu(QMenu):

    def __init__(self, roi: Roi):
        QMenu.__init__(self)
        self.roi = roi
        self.key = roi.key
        self.roi_dict = App().roi_dict
        self._init_menu()

        if App().debug_tracker:
            App().debug_tracker.add_object(self)

        self.exec_(QCursor.pos())
        # self.exec_(ev.globalPos())


class RoiContextMenu(AbstractRoiContextMenu):
    def _init_menu(self):
        self._init_rename_menu()
        self.addSeparator()
        self._init_type_menu()
        self.addSeparator()
        self._init_fix_menu()
        self.addSeparator()
        self._init_copy_menu()
        self.addSeparator()
        self._init_select_menu()
        self.addSeparator()
        self._init_fit_menu()
        self.addSeparator()
        self._init_delete_menu()

    def _init_fix_menu(self):
        fix_menu = self.addMenu('Fix/Unfix')
        if self.roi.movable:
            fix_action = fix_menu.addAction('Fix roi')
            fix_action.triggered.connect(lambda: self.roi_dict.fix_roi(self.key))
        else:
            fix_action = fix_menu.addAction('Unfix roi')
            fix_action.triggered.connect(lambda: self.roi_dict.unfix_roi(self.key))

        fix_selected = fix_menu.addAction('Fix selected roi')
        fix_selected.triggered.connect(self.roi_dict.fix_selected)
        unfix_selected = fix_menu.addAction('Unfix selected roi')
        unfix_selected.triggered.connect(self.roi_dict.unfix_selected)

        fix_all = fix_menu.addAction('Fix all roi')
        fix_all.triggered.connect(self.roi_dict.fix_all)

        unfix_all = fix_menu.addAction('Unix all roi')
        unfix_all.triggered.connect(self.roi_dict.unfix_all)

    def _init_delete_menu(self):
        delete_menu = self.addMenu('Delete')
        delete_self = delete_menu.addAction('Delete this roi')
        delete_self.triggered.connect(lambda: self.roi_dict.delete_roi(self.key))
        delete_selected = delete_menu.addAction('Delete selected')
        delete_selected.triggered.connect(self.roi_dict.delete_selected_roi)

    def _init_select_menu(self):
        select_menu = self.addMenu('Select')
        select_all = select_menu.addAction('Select all')
        select_all.triggered.connect(self.roi_dict.select_all)
        unselect_all = select_menu.addAction('Unselect all')
        unselect_all.triggered.connect(self.roi_dict.unselect_all)

    def _init_rename_menu(self):
        rename = self.addMenu('Rename')
        rename_action = QWidgetAction(self)
        line_edit = QLineEdit(self.roi.name)
        line_edit.editingFinished.connect(
            lambda: self.roi_dict.change_name(self.key, line_edit.text())
        )
        rename_action.setDefaultWidget(line_edit)
        rename.addAction(rename_action)

    def _init_type_menu(self):
        if self.roi.type == RoiTypes.ring:
            new_type = RoiTypes.segment
            change_type_name = 'segment'
        else:
            new_type = RoiTypes.ring
            change_type_name = 'ring'
        change_type_action = self.addAction(f'Change type to {change_type_name}')
        change_type_action.triggered.connect(
            lambda: self._change_roi_type(new_type))

    def _change_roi_type(self, new_type: RoiTypes):
        self.roi.type = new_type
        self.roi_dict.change_roi_type(self.key)

    def _init_fit_menu(self):
        fit_menu = self.addMenu('Fit')
        fit_selected = fit_menu.addAction('Fit selected rois')
        fit_selected.triggered.connect(lambda: self.roi_dict.open_fit_rois(True))
        fit_selected = fit_menu.addAction('Fit all rois')
        fit_selected.triggered.connect(lambda: self.roi_dict.open_fit_rois(False))

    def _init_copy_menu(self):
        copy_menu = self.addMenu('Copy/Paste')
        copy_menu.addAction('Copy roi', lambda: self.roi_dict.copy_rois(self.roi.key))
        copy_menu.addAction('Copy selected rois', lambda: self.roi_dict.copy_rois('selected'))
        copy_menu.addAction('Copy all rois', lambda: self.roi_dict.copy_rois('all'))
        if self.roi_dict.is_copied:
            copy_menu.addAction('Paste rois', lambda: self.roi_dict.paste_rois())

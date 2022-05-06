# SPDX-License-Identifier: MIT
# Copyright @ Yunseong Ha
# For more information, see
# https://github.com/yuj09161/PythonQtHangulInput/blob/master/LICENSE

from PySide6.QtCore import QCoreApplication, QObject, QEvent, Qt, Signal
from PySide6.QtGui import QFocusEvent, QKeyEvent
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QWidget

from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Union


class _Status_Types(Enum):
    CHOSEONG = auto()
    JUNGSEONG = auto()
    JUNGSEONG_IJUNG = auto()
    JONGSEONG = auto()
    JONGSEONG_SSANG = auto()
    JONGSEONG_GEOP = auto()
    MOEUM = auto()
    MOEUM_COMBINED = auto()


_JAEUM_KEYS: Dict[Qt.Key, Tuple[int, Union[int, None]]] = {
    Qt.Key_R: (0, 1),
    Qt.Key_S: (3, None),
    Qt.Key_E: (6, 7),
    Qt.Key_F: (8, None),
    Qt.Key_A: (16, None),
    Qt.Key_Q: (17, 18),
    Qt.Key_T: (20, 21),
    Qt.Key_D: (22, None),
    Qt.Key_W: (23, 24),
    Qt.Key_C: (25, None),
    Qt.Key_Z: (26, None),
    Qt.Key_X: (27, None),
    Qt.Key_V: (28, None),
    Qt.Key_G: (29, None)
}
_MOEUM_KEYS: Dict[Qt.Key, Tuple[int, int]] = {
    Qt.Key_K: (0, 0),
    Qt.Key_O: (1, 3),
    Qt.Key_I: (2, 2),
    Qt.Key_J: (4, 4),
    Qt.Key_P: (5, 7),
    Qt.Key_U: (6, 6),
    Qt.Key_H: (8, 8),
    Qt.Key_Y: (12, 12),
    Qt.Key_N: (13, 13),
    Qt.Key_B: (17, 17),
    Qt.Key_M: (18, 18),
    Qt.Key_L: (20, 20),
}
_JAEUM_COMBINATIONS: Dict[Tuple[int, int], int] = {
    (0, 20): 2,
    (3, 23): 4,
    (3, 29): 5,
    (8, 0): 9,
    (8, 16): 10,
    (8, 17): 11,
    (8, 20): 12,
    (8, 27): 13,
    (8, 28): 14,
    (8, 29): 15,
    (17, 20): 19,
}
_MOEUM_COMBINATIONS: Dict[Tuple[int, int], int] = {
    (8, 0): 9,
    (8, 1): 10,
    (8, 20): 11,
    (13, 4): 14,
    (13, 5): 15,
    (13, 20): 16,
}
_JAEUM_TO_CHOSEONG: Dict[int, int] = {
    0: 0,
    1: 1,
    3: 2,
    6: 3,
    7: 4,
    8: 5,
    16: 6,
    17: 7,
    18: 8,
    20: 9,
    21: 10,
    22: 11,
    23: 12,
    24: 13,
    25: 14,
    26: 15,
    27: 16,
    28: 17,
    29: 18,
}
_JAEUM_TO_JONGSEONG: Dict[int, int] = {
    0: 1,
    1: 2,
    2: 3,
    3: 4,
    4: 5,
    5: 6,
    6: 7,
    8: 8,
    9: 9,
    10: 10,
    11: 11,
    12: 12,
    13: 13,
    14: 14,
    15: 15,
    16: 16,
    17: 17,
    19: 18,
    20: 19,
    21: 20,
    22: 21,
    23: 22,
    25: 23,
    26: 24,
    27: 25,
    28: 26,
    29: 27,
}


class PythonQtHangulInputFilter(QObject):
    hangul_status_changed = Signal(bool)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self.__app = QCoreApplication.instance()
        if self.__app is None:
            raise RuntimeError(
                'A instance of QCoreApplication is not present.'
            )

        self.__is_hangul_mode: bool = False
        self.__do_not_remove_prev_chr: bool = False
        self.__prev_keys: List[Tuple[_Status_Types, int]] = []

    def reset(self):
        self.__is_hangul_mode = False
        self.__do_not_remove_prev_chr = False
        self.__prev_keys = []

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if isinstance(event, QFocusEvent)\
                and event.type() == QEvent.FocusOut:
            self.__prev_keys = []
            return False

        if not isinstance(event, QKeyEvent)\
                or event.type() != QEvent.KeyPress:
            return False

        key = event.key()
        if key == Qt.Key_Hangul:
            if self.__is_hangul_mode:
                self.__is_hangul_mode = False
                self.hangul_status_changed.emit(False)
                self.__prev_keys = []
            else:
                self.__is_hangul_mode = True
                self.hangul_status_changed.emit(True)
            return True
        if not self.__is_hangul_mode:
            return False

        if key == Qt.Key_Backspace:
            if not event.isAutoRepeat() and self.__prev_keys:
                del self.__prev_keys[-1]
                self.__remove_char(source)
                self.__show_input(source, False)
                return True
            return False

        modifiers = event.modifiers()
        if modifiers & ~Qt.ShiftModifier:
            self.__prev_keys = []
            return False

        shift_pressed = bool(modifiers & Qt.ShiftModifier)
        if key in _JAEUM_KEYS:
            codes = _JAEUM_KEYS.get(key)
            assert codes is not None, "Unknown error: variable 'codes' is None"
            code = codes[shift_pressed]
            if code is None:
                is_ssangjaeum = False
                code, _ = codes
            else:
                is_ssangjaeum = shift_pressed
            self.__update_status(True, is_ssangjaeum, code, source)
            return True
        if key in _MOEUM_KEYS:
            self.__update_status(
                False, False, _MOEUM_KEYS[key][shift_pressed], source
            )
            return True

        if key not in (0, Qt.Key_Shift):
            self.__prev_keys = []
        return False

    def __update_status(
        self, is_jaeum: bool, is_ssangjaeum: bool, code: int,
        to_display: QObject
    ) -> None:
        def reset_and_recurse():
            self.__prev_keys = []
            self.__update_status(is_jaeum, is_ssangjaeum, code, to_display)

        def on_moeum_later_jongseong():
            new_prev_keys =\
                [(_Status_Types.CHOSEONG, self.__prev_keys[-1][1])]
            del self.__prev_keys[-1]
            self.__show_input(to_display)
            self.__do_not_remove_prev_chr = True
            self.__prev_keys = new_prev_keys
            self.__update_status(is_jaeum, is_ssangjaeum, code, to_display)

        if not self.__prev_keys:
            if not is_jaeum:
                self.__prev_keys.append((_Status_Types.MOEUM, code))
            else:
                self.__prev_keys.append((_Status_Types.CHOSEONG, code))
            self.__show_input(to_display)
            return

        prev_type, prev_code = self.__prev_keys[-1]

        if prev_type == _Status_Types.CHOSEONG:
            if not is_jaeum:
                self.__prev_keys.append((_Status_Types.JUNGSEONG, code))
            else:
                reset_and_recurse()
                return

        elif prev_type == _Status_Types.JUNGSEONG:
            if is_jaeum:
                if code in _JAEUM_TO_JONGSEONG:
                    self.__prev_keys.append((
                        _Status_Types.JONGSEONG_SSANG
                        if is_ssangjaeum
                        else _Status_Types.JONGSEONG,
                        code
                    ))
                else:
                    reset_and_recurse()
                    return
            else:
                jungseongs = (prev_code, code)
                if jungseongs in _MOEUM_COMBINATIONS:
                    self.__prev_keys.append(
                        (_Status_Types.JUNGSEONG_IJUNG, code)
                    )
                else:
                    reset_and_recurse()
                    return

        elif prev_type == _Status_Types.JUNGSEONG_IJUNG:
            if not is_jaeum or code not in _JAEUM_TO_JONGSEONG:
                reset_and_recurse()
                return
            self.__prev_keys.append((
                _Status_Types.JONGSEONG_SSANG
                if is_ssangjaeum
                else _Status_Types.JONGSEONG,
                code
            ))

        elif prev_type == _Status_Types.JONGSEONG:
            if is_jaeum:
                if (prev_code, code) in _JAEUM_COMBINATIONS:
                    self.__prev_keys.append(
                        (_Status_Types.JONGSEONG_GEOP, code)
                    )
                else:
                    reset_and_recurse()
                    return
            else:
                on_moeum_later_jongseong()
                return

        elif prev_type in (
            _Status_Types.JONGSEONG_SSANG, _Status_Types.JONGSEONG_GEOP
        ):
            if is_jaeum:
                reset_and_recurse()
            else:
                on_moeum_later_jongseong()
            return

        elif prev_type == _Status_Types.MOEUM:
            if not is_jaeum and (prev_code, code) in _MOEUM_COMBINATIONS:
                self.__prev_keys.append(
                    (_Status_Types.MOEUM_COMBINED, code)
                )
            else:
                reset_and_recurse()
                return

        elif prev_type == _Status_Types.MOEUM_COMBINED:
            reset_and_recurse()
            return

        self.__show_input(to_display)

    def __show_input(
        self, to_display: QObject, remove_left_chr: Optional[bool] = None
    ) -> None:
        char = self.__get_current_char()
        len_prev_keys = len(self.__prev_keys)
        if len_prev_keys == 0:
            return
        if remove_left_chr is not None:
            if remove_left_chr:
                self.__remove_char(to_display)
        elif len_prev_keys != 1 and not self.__do_not_remove_prev_chr:
            self.__remove_char(to_display)
        self.__write_char(to_display, 0, char)
        self.__do_not_remove_prev_chr = False

    def __get_current_char(self) -> str:
        len_prev_keys = len(self.__prev_keys)
        if len_prev_keys == 0:
            return ''

        if self.__prev_keys[0][0] == _Status_Types.MOEUM:
            if len_prev_keys == 1:
                code = self.__prev_keys[0][1]
            else:
                code = _MOEUM_COMBINATIONS[
                    (self.__prev_keys[0][1], self.__prev_keys[1][1])
                ]
            return chr(code + 0x314F)

        if len_prev_keys == 1:
            return chr(self.__prev_keys[0][1] + 0x3131)

        it = iter(reversed(self.__prev_keys))
        result_code = 0
        try:
            while True:
                type_, code = next(it)
                if type_ == _Status_Types.JUNGSEONG_IJUNG:
                    type_, code1 = next(it)
                    assert type_ == _Status_Types.JUNGSEONG
                    code = _MOEUM_COMBINATIONS[(code1, code)]
                elif type_ == _Status_Types.JONGSEONG_GEOP:
                    type_, code1 = next(it)
                    assert type_ == _Status_Types.JONGSEONG
                    code = _JAEUM_COMBINATIONS[(code1, code)]

                if type_ == _Status_Types.CHOSEONG:
                    result_code += _JAEUM_TO_CHOSEONG[code] * 588
                    break
                elif type_ == _Status_Types.JUNGSEONG:
                    result_code += code * 28
                elif type_ in (
                    _Status_Types.JONGSEONG, _Status_Types.JONGSEONG_SSANG
                ):
                    result_code += _JAEUM_TO_JONGSEONG[code]
        except StopIteration:
            pass
        return chr(result_code + 0xAC00)

    def __remove_char(self, to: QObject):
        assert self.__app is not None
        self.__app.postEvent(to, QKeyEvent(
            QEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier, '\b', True, 2
        ))
        self.__app.postEvent(to, QKeyEvent(
            QEvent.KeyRelease, Qt.Key_Backspace, Qt.NoModifier, '\b', True, 2
        ))

    def __write_char(
        self, to: QObject, key: int, char: str,
        modifiers: Qt.KeyboardModifier = Qt.NoModifier
    ):
        assert self.__app is not None
        assert len(char) == 1, "'char' argument is not a charactor."
        self.__app.postEvent(
            to, QKeyEvent(QEvent.KeyPress, key, modifiers, char)
        )
        self.__app.postEvent(
            to, QKeyEvent(QEvent.KeyRelease, key, modifiers)
        )


class HangulIndicator(QDialog):
    setPosition = Signal(int, int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setModal(False)
        self.setWindowFlags(
            (self.windowFlags() | Qt.FramelessWindowHint)
            & ~(Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        )

        self.hlMain = QHBoxLayout(self)
        self.hlMain.setContentsMargins(7, 7, 7, 7)
        self.lbMain = QLabel('\ud55c', self)
        self.lbMain.setStyleSheet('color: #000000')
        self.hlMain.addWidget(self.lbMain)

        self.setFixedSize(self.sizeHint())

        self.setPosition.connect(self.__set_position)

    def set_hangul_status(self, status: bool) -> None:
        self.lbMain.setStyleSheet(
            'color: #0000ff; font-weight: bold' if status else 'color: #000000'
        )

    def __set_position(self, x: int, y: int) -> None:
        geometry = self.geometry()
        self.setGeometry(x, y, geometry.width(), geometry.height())

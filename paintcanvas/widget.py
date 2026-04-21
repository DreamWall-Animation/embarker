from PySide6 import QtGui, QtWidgets, QtCore


class SliderSetValueAtClickPosition(QtWidgets.QSlider):

    def mousePressEvent(self, event):
        """
        Set value at clicked value and start handle.
        """
        if event.button() != QtCore.Qt.LeftButton:
            return super().mousePressEvent(event)

        opt = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(opt)
        handle_rect = self.style().subControlRect(
            QtWidgets.QStyle.CC_Slider, opt,
            QtWidgets.QStyle.SC_SliderHandle, self)

        if handle_rect.contains(event.pos()):
            return super().mousePressEvent(event)

        if self.orientation() == QtCore.Qt.Horizontal:
            pos = event.position().x()
            slider_length = self.width()
        else:
            pos = event.position().y()
            slider_length = self.height()

        new_value = (
            self.minimum() +
            ((self.maximum() - self.minimum()) * pos) //
            slider_length)
        self.setValue(int(new_value))

        fake_event = QtGui.QMouseEvent(
            QtGui.QMouseEvent.MouseButtonPress,
            event.position(),
            QtCore.Qt.LeftButton,
            QtCore.Qt.LeftButton,
            QtCore.Qt.NoModifier)
        return super().mousePressEvent(fake_event)

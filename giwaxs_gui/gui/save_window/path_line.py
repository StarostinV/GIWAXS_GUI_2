from ...app.data_manager import SavingParameters
from ..basic_widgets import H5PathLine, PathLineModes


class SavePathLine(H5PathLine):

    def update_params(self, saving_params: SavingParameters):
        saving_params.path = self.path

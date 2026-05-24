from aiogram.fsm.state import State, StatesGroup

class SearchStates(StatesGroup):
    choosing_district  = State()
    choosing_category  = State()

class RegisterStates(StatesGroup):
    choosing_category  = State()
    choosing_district  = State()
    entering_name      = State()
    entering_phone     = State()
    entering_desc      = State()
    entering_address   = State()
    confirming         = State()

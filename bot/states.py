from aiogram.fsm.state import State, StatesGroup

class SearchStates(StatesGroup):
    choosing_oblast    = State()
    choosing_district  = State()
    choosing_category  = State()
    typing_query       = State()

class RegisterStates(StatesGroup):
    choosing_category  = State()
    choosing_oblast    = State()
    choosing_district  = State()
    entering_name      = State()
    entering_phone     = State()
    entering_desc      = State()
    entering_address   = State()
    entering_social    = State()
    confirming         = State()

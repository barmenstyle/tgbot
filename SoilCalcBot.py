import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = "7569043559:AAGEErj7E0DbgQbqXtquHx0TMnujlGbJmRg"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Параметры для каждого типа грунта (c, f, e)
SAND_TYPES = {
    "Гравелистые и крупные": ((2, 1), (43, 38), (50, 40)),
    "Средней крупности": ((3, 2), (40, 35), (50, 40)),
    "Мелкие": ((6, 4), (38, 32), (48, 38)),
    "Пылеватые": ((8, 6), (36, 30), (39, 28))
}

MAIN_MENU = {
    "Пески",
    "Глины",
    "about"
}

CLAY_TYPES = {
    "Прочностные c, ф",
    "Деформационные"
}

CLAY_TYPES_A = {

}

# Константы
POROSITY_LOW = 0.45
POROSITY_MID_C = 0.55
POROSITY_MID_F = 0.65


# Состояния FSM
class Form(StatesGroup):
    choosing_sand = State()
    entering_porosity = State()
    choose = State()
    choosing_clay = State()


# Главное меню
def build_main_menu():
    builder = ReplyKeyboardBuilder()
    for item in MAIN_MENU:
        builder.add(types.KeyboardButton(text=item))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# Пески
def build_sand_keyboard():
    builder = ReplyKeyboardBuilder()
    for sand_type in SAND_TYPES:
        builder.add(types.KeyboardButton(text=sand_type))
    builder.add(types.KeyboardButton(text="Назад в меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def build_clay_keyboard():
    builder = ReplyKeyboardBuilder()

    builder.add(types.KeyboardButton(text="Назад в меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# Стартовая команда
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "Добро пожаловать!\nВыберите действие:",
        reply_markup=build_main_menu()
    )
    await state.set_state(Form.choose)


# Выбор песка
@dp.message(Form.choose, F.text == "Пески")
async def handle_sands(message: types.Message, state: FSMContext):
    await message.answer(
        "Выберите тип песка:",
        reply_markup=build_sand_keyboard()
    )
    await state.set_state(Form.choosing_sand)


@dp.message(Form.choose, F.text == "Глины")
async def handle_clay(message: types.Message, state: FSMContext):
    await message.answer(
        "Раздел в разработке",
        reply_markup=build_clay_keyboard()
    )
    await state.set_state(Form.choosing_clay)


# Обработка выбора типа грунта
@dp.message(Form.choosing_sand, F.text.in_(SAND_TYPES))
async def sand_chosen(message: types.Message, state: FSMContext):
    await state.update_data(sand_type=message.text)
    await message.answer(
        f"Вы выбрали: {message.text}\n"
        "Теперь введите пористость грунта:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Form.entering_porosity)


# Обработка некорректного выбора типа грунта
@dp.message(Form.choosing_soil)
async def incorrect_soil(message: types.Message):
    await message.answer("Пожалуйста, выберите тип грунта из предложенных вариантов.")


# Расчет параметров грунта
@dp.message(Form.entering_porosity)
async def calculate_params(message: types.Message, state: FSMContext):
    try:
        pore = float(message.text)
        if pore < 0 or pore > 1:
            await message.answer("Пористость должна быть в диапазоне от 0 до 1. Попробуйте снова:")
            return

        user_data = await state.get_data()
        sand_type = user_data['sand_type']
        c_range, f_range, e_range = SAND_TYPES[sand_type]

        c = abs(c_range[0] + ((pore - POROSITY_LOW) /
                              (POROSITY_MID_C - POROSITY_LOW) * (c_range[1] - c_range[0])))
        f = abs(f_range[0] + ((pore - POROSITY_LOW) /
                              (POROSITY_MID_F - POROSITY_LOW) * (f_range[1] - f_range[0])))
        e = abs(e_range[0] + ((pore - POROSITY_LOW) /
                              (POROSITY_MID_C - POROSITY_LOW) * (e_range[1] - e_range[0])))

        result_text = (
            f"Результаты для {sand_type} с пористостью {pore}:\n\n"
            f"c = {round(c / 1000, 3)}\n"
            f"ф = {round(f, 3)}\n"
            f"E = {round(e, 3)}"
        )

        builder = ReplyKeyboardBuilder()
        for sand_type in SAND_TYPES:
            builder.add(types.KeyboardButton(text=sand_type))
        builder.adjust(2)

        await message.answer(
            result_text,
            reply_markup=builder.as_markup(resize_keyboard=True)
        )
        await state.set_state(Form.choosing_soil)

    except ValueError:
        await message.answer("Пожалуйста, введите число:")


# Обработка команды отмены
@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Работа с калькулятором завершена. "
        "Если хотите начать заново, отправьте /start",
        reply_markup=types.ReplyKeyboardRemove()
    )


# Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
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
SOIL_TYPES = {
    "Гравелистые и крупные": ((2, 1), (43, 38), (50, 40)),
    "Средней крупности": ((3, 2), (40, 35), (50, 40)),
    "Мелкие": ((6, 4), (38, 32), (48, 38)),
    "Пылеватые": ((8, 6), (36, 30), (39, 28))
}

# Константы
POROSITY_LOW = 0.45
POROSITY_MID_C = 0.55
POROSITY_MID_F = 0.65


# Состояния FSM
class Form(StatesGroup):
    choosing_soil = State()
    entering_porosity = State()


# Стартовая команда
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    for soil_type in SOIL_TYPES:
        builder.add(types.KeyboardButton(text=soil_type))
    builder.adjust(2)

    await message.answer(
        "Добро пожаловать в калькулятор параметров грунта!\n"
        "Выберите тип грунта:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(Form.choosing_soil)


# Обработка выбора типа грунта
@dp.message(Form.choosing_soil, F.text.in_(SOIL_TYPES))
async def soil_chosen(message: types.Message, state: FSMContext):
    await state.update_data(soil_type=message.text)
    await message.answer(
        f"Вы выбрали: {message.text}\n"
        "Теперь введите пористость грунта (число от 0.45 до 0.65):",
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
        soil_type = user_data['soil_type']
        c_range, f_range, e_range = SOIL_TYPES[soil_type]

        c = abs(c_range[0] + ((pore - POROSITY_LOW) /
                              (POROSITY_MID_C - POROSITY_LOW) * (c_range[1] - c_range[0])))
        f = abs(f_range[0] + ((pore - POROSITY_LOW) /
                              (POROSITY_MID_F - POROSITY_LOW) * (f_range[1] - f_range[0])))
        e = abs(e_range[0] + ((pore - POROSITY_LOW) /
                              (POROSITY_MID_C - POROSITY_LOW) * (e_range[1] - e_range[0])))

        result_text = (
            f"Результаты для {soil_type} с пористостью {pore}:\n\n"
            f"c = {round(c, 2)}\n"
            f"ф = {round(f, 2)}\n"
            f"E = {round(e, 2)}"
        )

        builder = ReplyKeyboardBuilder()
        for soil_type in SOIL_TYPES:
            builder.add(types.KeyboardButton(text=soil_type))
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
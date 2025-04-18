import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация (токен теперь берется из переменных окружения)
BOT_TOKEN = "7569043559:AAGEErj7E0DbgQbqXtquHx0TMnujlGbJmRg"
if not BOT_TOKEN:
    raise ValueError("Не установлен BOT_TOKEN в переменных окружения")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Константы вынесены в отдельный блок
class SoilConstants:
    POROSITY_LOW = 0.45
    POROSITY_MID_C = 0.55
    POROSITY_MID_F = 0.65
    POROSITY_HIGH = 0.75
    POROSITY_CLAY_MAX = 1.05


class SoilData:
    SAND_TYPES = {
        "Гравелистые и крупные": ((2, 1), (43, 38), (50, 40)),
        "Средней крупности": ((3, 2), (40, 35), (50, 40)),
        "Мелкие": ((6, 4), (38, 32), (48, 38)),
        "Пылеватые": ((8, 6), (36, 30), (39, 28))
    }

    CLAY_TYPES = {
        "Прочностные c, ф": "CLAY_STRENGTH",
        "Деформационные": "CLAY_DEFORMATION"
    }

    # Обновленные параметры для глин с учетом показателя текучести
    CLAY_STRENGTH_PARAMS = {
        "Суглинки": {
            "0 ≤ I ≤ 0.25": ((31, 25), (24, 23)),
            "0.25 < I ≤ 0.5": ((28, 23), (22, 21)),
            "0.5 < I ≤ 0.75": ((25, 20), (19, 18))
        },
        "Супеси": {
            "0 ≤ I ≤ 0.25": ((15, 13), (27, 24)),
            "0.25 < I ≤ 0.75": ((13, 11), (24, 21))
        },
        "Глины": {
            "0 ≤ I ≤ 0.25": ((68, 54), (20, 19)),
            "0.25 < I ≤ 0.5": ((57, 50), (18, 17)),
            "0.5 < I ≤ 0.75": ((45, 41), (15, 14))
        }
    }

    MAIN_MENU_OPTIONS = {"Пески", "Глины", "О боте"}


# Состояния FSM
class Form(StatesGroup):
    main_menu = State()
    choosing_sand = State()
    choosing_clay = State()
    choosing_clay_strength = State()
    entering_porosity_sand = State()
    entering_porosity_clay = State()


# Клавиатуры вынесены в отдельные функции
class Keyboards:
    @staticmethod
    def build_main_menu():
        builder = ReplyKeyboardBuilder()
        for item in SoilData.MAIN_MENU_OPTIONS:
            builder.add(types.KeyboardButton(text=item))
        builder.adjust(2)
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def build_sand_types():
        builder = ReplyKeyboardBuilder()
        for sand_type in SoilData.SAND_TYPES:
            builder.add(types.KeyboardButton(text=sand_type))
        builder.add(types.KeyboardButton(text="Назад в меню"))
        builder.adjust(2)
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def build_clay_types():
        builder = ReplyKeyboardBuilder()
        for clay_type in SoilData.CLAY_TYPES:
            builder.add(types.KeyboardButton(text=clay_type))
        builder.add(types.KeyboardButton(text="Назад в меню"))
        builder.adjust(2)
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def build_clay_strength_types():
        builder = ReplyKeyboardBuilder()
        for clay_type in SoilData.CLAY_STRENGTH_PARAMS:
            builder.add(types.KeyboardButton(text=clay_type))
        builder.add(types.KeyboardButton(text="Назад"))
        builder.adjust(2)
        return builder.as_markup(resize_keyboard=True)

    @staticmethod
    def build_fluidity_ranges(clay_type: str):
        builder = ReplyKeyboardBuilder()
        for fluidity_range in SoilData.CLAY_STRENGTH_PARAMS[clay_type]:
            builder.add(types.KeyboardButton(text=fluidity_range))
        builder.add(types.KeyboardButton(text="Назад"))
        builder.adjust(1)
        return builder.as_markup(resize_keyboard=True)



# Валидация ввода
def validate_porosity(value: str, max_value: float = 1.0) -> float:
    try:
        pore = float(value)
        if not 0 <= pore <= max_value:
            raise ValueError(f"Пористость должна быть в диапазоне от 0 до {max_value}")
        return pore
    except ValueError as e:
        raise ValueError("Пожалуйста, введите корректное число") from e


# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(Form.main_menu)
    await message.answer(
        "Добро пожаловать в бот для расчета параметров грунта!\n"
        "Выберите тип грунта:",
        reply_markup=Keyboards.build_main_menu()
    )
    logger.info(f"User {message.from_user.id} started the bot")


@dp.message(Command("cancel"))
@dp.message(F.text.casefold() == "отмена")
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Работа с калькулятором завершена. "
        "Если хотите начать заново, отправьте /start",
        reply_markup=types.ReplyKeyboardRemove()
    )
    logger.info(f"User {message.from_user.id} canceled operation")


# Главное меню
@dp.message(Form.main_menu, F.text == "Пески")
async def handle_sands(message: types.Message, state: FSMContext):
    await state.set_state(Form.choosing_sand)
    await message.answer(
        "Выберите тип песка:",
        reply_markup=Keyboards.build_sand_types()
    )


@dp.message(Form.main_menu, F.text == "Глины")
async def handle_clays(message: types.Message, state: FSMContext):
    await state.set_state(Form.choosing_clay)
    await message.answer(
        "Выберите тип параметров для глин:",
        reply_markup=Keyboards.build_clay_types()
    )


@dp.message(Form.main_menu, F.text == "О боте")
async def handle_about(message: types.Message):
    await message.answer(
        "Этот бот помогает рассчитывать параметры грунта.\n"
        "Разработано для инженерно-геологических изысканий.\n"
        "@barmenstyle ver.0.2"
    )


# Обработка выбора песка
@dp.message(Form.choosing_sand, F.text.in_(SoilData.SAND_TYPES))
async def sand_type_chosen(message: types.Message, state: FSMContext):
    await state.update_data(sand_type=message.text)
    await state.set_state(Form.entering_porosity_sand)
    await message.answer(
        f"Вы выбрали: {message.text}\n"
        "Введите пористость грунта (от 0 до 1):",
        reply_markup=types.ReplyKeyboardRemove()
    )


@dp.message(Form.choosing_sand, F.text == "Назад в меню")
async def back_to_menu_from_sand(message: types.Message, state: FSMContext):
    await state.set_state(Form.main_menu)
    await message.answer(
        "Выберите тип грунта:",
        reply_markup=Keyboards.build_main_menu()
    )


# Обработка выбора глины
@dp.message(Form.choosing_clay, F.text == "Прочностные c, ф")
async def clay_strength_chosen(message: types.Message, state: FSMContext):
    await state.set_state(Form.choosing_clay_strength)
    await message.answer(
        "Выберите тип глины:",
        reply_markup=Keyboards.build_clay_strength_types()
    )


@dp.message(Form.choosing_clay, F.text == "Деформационные")
async def clay_deformation_chosen(message: types.Message):
    await message.answer(
        "Этот раздел в разработке. Проверьте позже.",
        reply_markup=Keyboards.build_clay_types()
    )


@dp.message(Form.choosing_clay, F.text == "Назад в меню")
async def back_to_menu_from_clay(message: types.Message, state: FSMContext):
    await state.set_state(Form.main_menu)
    await message.answer(
        "Выберите тип грунта:",
        reply_markup=Keyboards.build_main_menu()
    )


@dp.message(Form.choosing_clay, F.text == "Прочностные c, ф")
async def clay_strength_chosen(message: types.Message, state: FSMContext):
    await state.set_state(Form.choosing_clay_strength)
    await message.answer(
        "Выберите тип глины:",
        reply_markup=Keyboards.build_clay_strength_types()
    )


# Новое состояние для выбора показателя текучести
class Form(StatesGroup):
    main_menu = State()
    choosing_sand = State()
    choosing_clay = State()
    choosing_clay_strength = State()
    choosing_fluidity_range = State()  # Новое состояние
    entering_porosity_sand = State()
    entering_porosity_clay = State()


# Обработчик выбора типа глины
@dp.message(Form.choosing_clay_strength, F.text.in_(SoilData.CLAY_STRENGTH_PARAMS))
async def clay_strength_type_chosen(message: types.Message, state: FSMContext):
    await state.update_data(clay_type=message.text)
    await state.set_state(Form.choosing_fluidity_range)
    await message.answer(
        f"Вы выбрали: {message.text}\n"
        "Выберите показатель текучести (I):",
        reply_markup=Keyboards.build_fluidity_ranges(message.text)
    )


# Обработчик выбора показателя текучести
@dp.message(Form.choosing_fluidity_range, F.text.in_({
    "0 ≤ I ≤ 0.25", "0.25 < I ≤ 0.5", "0.5 < I ≤ 0.75", "0.25 < I ≤ 0.75"
}))
async def fluidity_range_chosen(message: types.Message, state: FSMContext):
    data = await state.get_data()
    clay_type = data['clay_type']
    fluidity_range = message.text

    # Сохраняем выбранный диапазон текучести
    await state.update_data(fluidity_range=fluidity_range)

    await state.set_state(Form.entering_porosity_clay)
    await message.answer(
        f"Вы выбрали: {clay_type}, {fluidity_range}\n"
        "Введите пористость грунта (от 0 до 1.05):",
        reply_markup=types.ReplyKeyboardRemove()
    )


# Возврат к выбору типа глины
@dp.message(Form.choosing_fluidity_range, F.text == "Назад")
async def back_to_clay_types_from_fluidity(message: types.Message, state: FSMContext):
    await state.set_state(Form.choosing_clay_strength)
    await message.answer(
        "Выберите тип глины:",
        reply_markup=Keyboards.build_clay_strength_types()
    )


# Обновленный расчет для глин
@dp.message(Form.entering_porosity_clay)
async def calculate_clay_params(message: types.Message, state: FSMContext):
    try:
        porosity = validate_porosity(message.text, SoilConstants.POROSITY_CLAY_MAX)
        data = await state.get_data()
        clay_type = data['clay_type']
        fluidity_range = data['fluidity_range']

        # Получаем параметры для выбранного типа глины и диапазона текучести
        c_range, f_range = SoilData.CLAY_STRENGTH_PARAMS[clay_type][fluidity_range]

        # Расчет параметров
        c = abs(c_range[0] + ((porosity - SoilConstants.POROSITY_MID_F) /
                              (SoilConstants.POROSITY_HIGH - SoilConstants.POROSITY_MID_F) *
                              (c_range[1] - c_range[0])))

        f = abs(f_range[0] + ((porosity - SoilConstants.POROSITY_MID_F) /
                              (SoilConstants.POROSITY_HIGH - SoilConstants.POROSITY_MID_F) *
                              (f_range[1] - f_range[0])))

        result = (
            f"Результаты для {clay_type} ({fluidity_range}) с пористостью {porosity}:\n\n"
            f"c = {round(c / 1000, 3)} МПа\n"
            f"φ = {round(f, 3)}°"
        )

        await message.answer(
            result,
            reply_markup=Keyboards.build_clay_strength_types()
        )
        await state.set_state(Form.choosing_clay_strength)
        logger.info(f"Calculated clay params for user {message.from_user.id}")

    except ValueError as e:
        await message.answer(str(e))
        logger.warning(f"User {message.from_user.id} entered invalid porosity: {message.text}")

# Расчеты для песка
@dp.message(Form.entering_porosity_sand)
async def calculate_sand_params(message: types.Message, state: FSMContext):
    try:
        porosity = validate_porosity(message.text)
        data = await state.get_data()
        sand_type = data['sand_type']

        c_range, f_range, e_range = SoilData.SAND_TYPES[sand_type]

        # Расчет параметров
        c = abs(c_range[0] + ((porosity - SoilConstants.POROSITY_LOW) /
                              (SoilConstants.POROSITY_MID_C - SoilConstants.POROSITY_LOW) *
                              (c_range[1] - c_range[0])))

        f = abs(f_range[0] + ((porosity - SoilConstants.POROSITY_LOW) /
                              (SoilConstants.POROSITY_MID_F - SoilConstants.POROSITY_LOW) *
                              (f_range[1] - f_range[0])))

        e = abs(e_range[0] + ((porosity - SoilConstants.POROSITY_LOW) /
                              (SoilConstants.POROSITY_MID_C - SoilConstants.POROSITY_LOW) *
                              (e_range[1] - e_range[0])))

        result = (
            f"Результаты для {sand_type} с пористостью {porosity}:\n\n"
            f"c = {round(c / 1000, 3)} МПа\n"
            f"φ = {round(f, 3)}°\n"
            f"E = {round(e, 3)} МПа"
        )

        await message.answer(
            result,
            reply_markup=Keyboards.build_sand_types()
        )
        await state.set_state(Form.choosing_sand)
        logger.info(f"Calculated sand params for user {message.from_user.id}")

    except ValueError as e:
        await message.answer(str(e))
        logger.warning(f"User {message.from_user.id} entered invalid porosity: {message.text}")


# Расчеты для глины
@dp.message(Form.entering_porosity_clay)
async def calculate_clay_params(message: types.Message, state: FSMContext):
    try:
        porosity = validate_porosity(message.text, SoilConstants.POROSITY_CLAY_MAX)
        data = await state.get_data()
        clay_type = data['clay_type']

        c_range, f_range = SoilData.CLAY_STRENGTH_PARAMS[clay_type]

        # Расчет параметров
        c = abs(c_range[0] + ((porosity - SoilConstants.POROSITY_MID_F) /
                              (SoilConstants.POROSITY_HIGH - SoilConstants.POROSITY_MID_F) *
                              (c_range[1] - c_range[0])))

        f = abs(f_range[0] + ((porosity - SoilConstants.POROSITY_MID_F) /
                              (SoilConstants.POROSITY_HIGH - SoilConstants.POROSITY_MID_F) *
                              (f_range[1] - f_range[0])))

        result = (
            f"Результаты для {clay_type} с пористостью {porosity}:\n\n"
            f"c = {round(c / 1000, 3)} МПа\n"
            f"φ = {round(f, 3)}°"
        )

        await message.answer(
            result,
            reply_markup=Keyboards.build_clay_strength_types()
        )
        await state.set_state(Form.choosing_clay_strength)
        logger.info(f"Calculated clay params for user {message.from_user.id}")

    except ValueError as e:
        await message.answer(str(e))
        logger.warning(f"User {message.from_user.id} entered invalid porosity: {message.text}")


# Запуск бота
async def main():
    try:
        logger.info("Starting bot")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
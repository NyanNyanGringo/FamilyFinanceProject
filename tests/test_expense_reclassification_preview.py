import unittest
from collections import Counter

from scripts.expense_reclassification_preview import (
    HIGH,
    MEDIUM,
    PARKING_TOLL_CATEGORY,
    PreviewError,
    REVIEW,
    Decision,
    GridBlock,
    Operation,
    RuleContext,
    animal_groups,
    approved_non_event_exception,
    assign_stable_ids,
    build_rule_context,
    category_data,
    classify_animal,
    classify_car,
    classify_home,
    classify_printing,
    classify_subscription,
    classify_transport,
    is_service_operation,
    lodging_override,
    markdown_escape,
    operation_row_hash,
    personal_care_or_health,
    psychology_override,
    regression_ids_pass,
    render_markdown,
    semantic_override,
    settings_expense_category_lists,
    user_approved_overrides_pass,
    user_approved_stable_override,
    validate_artifacts,
    valid_category_override,
)


def cell(value=None, formatted=None, validation=None):
    result = {}
    if value is not None:
        key = "numberValue" if isinstance(value, (int, float)) else "stringValue"
        result["effectiveValue"] = {key: value}
        result["userEnteredValue"] = {key: value}
    if formatted is not None:
        result["formattedValue"] = formatted
    if validation is not None:
        result["dataValidation"] = validation
    return result


def operation(values, row=7):
    cells = tuple(cell(value, str(value) if value is not None else "") for value in values)
    return Operation(row, cells, operation_row_hash(cells))


def expense_operation(before, comment, *, date=1, amount=10, currency="EUR", row=7):
    return operation([date, "", before, "Card", amount, currency, "Committed", amount, "EUR", comment, "", ""], row=row)


def rule_context(*operations, subscription_counts=None, same_day_comments=None):
    return RuleContext(
        tuple(operations),
        frozenset(),
        frozenset(),
        Counter(subscription_counts or {}),
        same_day_comments or {},
    )


def artifact_record(number, date, confidence, *, changed=True):
    amount = 10 if number == 1 else 20 if number == 2 else 0
    return {
        "n": number,
        "changed": changed,
        "before": "Before",
        "after": "After" if changed else "Before",
        "reason": "reason",
        "confidence": confidence,
        "rule": "test",
        "locator": {"snapshot_row_reference": 10 + int(number or 0)},
        "effective": {"date": {"numberValue": date}, "amount_eur": {"numberValue": amount}},
        "display": {
            "date": str(date),
            "amount": str(amount),
            "currency": "EUR",
            "amount_eur": str(amount),
            "main_currency": "EUR",
            "comment": "comment",
        },
    }


class PreviewPureFunctionTests(unittest.TestCase):
    def test_unique_telegram_id_is_preferred(self):
        first = operation([1, "", "A", "Card", 10, "EUR", "Committed", 10, "EUR", "x", "", 123])
        second = operation([2, "", "A", "Card", 20, "EUR", "Committed", 20, "EUR", "y", "", 124])

        identified = assign_stable_ids((first, second))

        self.assertEqual(identified[0].stable_id, "telegram:123")
        self.assertEqual(identified[0].match_count, 1)

    def test_duplicate_telegram_id_falls_back_to_fingerprint(self):
        first = operation([1, "", "A", "Card", 10, "EUR", "Committed", 10, "EUR", "x", "", 123])
        second = operation([2, "", "A", "Card", 20, "EUR", "Committed", 20, "EUR", "y", "", 123])

        identified = assign_stable_ids((first, second))

        self.assertTrue(identified[0].stable_id.startswith("fingerprint:v1:"))
        self.assertNotEqual(identified[0].stable_id, identified[1].stable_id)

    def test_service_row_is_recognized_by_content(self):
        values = [45292, "", "", "", 0, "", "Committed", 0, "EUR", "Это строка шаблона. Не удалять.", "", ""]

        self.assertTrue(is_service_operation(operation(values, row=999)))

    def test_allowed_categories_are_deduplicated(self):
        header = tuple(cell() for _ in range(8))
        row_one = tuple(cell() for _ in range(7)) + (cell("Другое", "Другое"),)
        row_two = tuple(cell() for _ in range(7)) + (cell("Другое", "Другое"),)
        block = GridBlock("*data", 1, 5, 29, (header, row_one, row_two))

        categories = category_data(block)

        self.assertEqual(categories["allowed"], ("Другое",))
        self.assertEqual(categories["duplicate_allowed"], ["Другое"])

    def test_lodging_word_boundary_does_not_match_trotelnik(self):
        self.assertIsNone(lodging_override("Другое", "купили тротельник"))

    def test_mobile_rule_does_not_match_automobile(self):
        self.assertIsNone(valid_category_override("Коммуналка", "ремонт автомобиля"))

    def test_psychologist_for_driving_documents_is_not_therapy(self):
        decision = psychology_override("Господин", "оплата психолога для водительских прав")

        self.assertEqual(decision.after, "ВНЖ ПМЖ")
        self.assertEqual(decision.confidence, HIGH)

    def test_psychology_webinar_is_education(self):
        decision = psychology_override("Госпожа", "оплата вебинара по психологии")

        self.assertEqual(decision.after, "Образование и изучение языков")

    def test_beauty_in_health_is_reclassified(self):
        decision = personal_care_or_health("Здоровье", "сыворотка для лица")

        self.assertEqual(decision.after, "Уход за собой")

    def test_gym_food_is_products(self):
        decision = valid_category_override("Тренажерный зал", "протеиновый батончик")

        self.assertEqual(decision.after, "Продукты")

    def test_markdown_escapes_pipes_and_newlines(self):
        self.assertEqual(markdown_escape("a|b\nc"), "a\\|b<br>c")

    def test_tire_stem_does_not_match_inside_car_word(self):
        ambiguous = classify_car(expense_operation("Машина", "Правила машины"))
        repair = classify_car(expense_operation("Машина", "Ремонт машины"))

        self.assertEqual(ambiguous.confidence, REVIEW)
        self.assertEqual(repair.after, "Ремонт машины")
        self.assertEqual(repair.confidence, HIGH)

    def test_car_driving_authorization_is_not_maintenance(self):
        item = expense_operation("Машина", "Оплата для Лизы бумажек, чтобы она могла водить машину одна за границей")

        decision = classify_car(item)

        self.assertEqual(decision.after, "ВНЖ ПМЖ")
        self.assertEqual(decision.confidence, REVIEW)

    def test_gifted_money_does_not_turn_hairbrush_into_gift(self):
        decision = semantic_override(expense_operation("Госпожа", "Озон Расческа на подаренные деньги"))

        self.assertEqual(decision.after, "Уход за собой")
        self.assertEqual(decision.confidence, HIGH)

    def test_pull_and_bear_typo_is_clothing(self):
        decision = semantic_override(expense_operation("Госпожа", "Pool and beer. Доставка. UPD: вернули деньги"))

        self.assertEqual(decision.after, "Одежда")

    def test_orthopedic_insoles_are_health(self):
        decision = semantic_override(expense_operation("Госпожа", "Стельки ортопедические"))

        self.assertEqual(decision.after, "Здоровье")

    def test_animal_consultation_about_does_not_match_leash(self):
        groups = animal_groups("Консультация по поводу лечения")

        self.assertEqual(groups, {"Ветеринар для Лунтинка"})

    def test_nextgard_is_veterinary(self):
        self.assertEqual(animal_groups("NextGard для собаки"), {"Ветеринар для Лунтинка"})

    def test_blank_animal_comment_uses_medium_same_day_context(self):
        item = expense_operation("Животные", "", date=42)
        context = rule_context(item, same_day_comments={(42, "Животные"): ("nextgard для собаки",)})

        decision = classify_animal(item, context)

        self.assertEqual(decision.after, "Ветеринар для Лунтинка")
        self.assertEqual(decision.confidence, MEDIUM)

    def test_ip_must_be_standalone_in_subscription_business_rule(self):
        item = expense_operation("Подписки", "Подписка на чат Джипити")
        context = rule_context(item, subscription_counts={"chatgpt": 2})

        decision = classify_subscription(item, context)

        self.assertEqual(decision.after, "Ежемесячные подписки")
        self.assertNotEqual(decision.rule, "subscription-business-ambiguous")

    def test_explicit_subscription_for_ip_uses_business_rule(self):
        item = expense_operation("Подписки", "Подписка для ИП")

        decision = classify_subscription(item, rule_context(item))

        self.assertEqual(decision.after, "ИП в России")
        self.assertEqual(decision.confidence, REVIEW)

    def test_home_specific_items_outrank_clothing_hints(self):
        cases = (
            "Бутылка для воды",
            "Постельное бельё",
            "Полотенце для зала в H&M",
            "Контейнер и кондиционер для одежды",
        )
        for comment in cases:
            with self.subTest(comment=comment):
                decision = semantic_override(expense_operation("Покупки в Дом", comment))
                self.assertEqual(decision.after, "Покупки в дом")
                self.assertEqual(decision.confidence, HIGH)

    def test_therapeutic_shampoo_stays_in_health(self):
        decision = semantic_override(expense_operation("Здоровье", "Шампунь против перхоти"))

        self.assertEqual(decision.after, "Здоровье")
        self.assertEqual(decision.rule, "unchanged")

    def test_color_adjective_is_not_a_flower_gift(self):
        pencils = semantic_override(expense_operation("Покупки в Дом", "цветные карандаши"))
        sheets = semantic_override(expense_operation("Покупки в Дом", "Купили листочки для Лизы, цветные"))
        plants = semantic_override(expense_operation("Покупки в Дом", "Оливковое дерево + 12 цветочков"))
        roses = semantic_override(expense_operation("Госпожа", "Купил розы Лизе"))

        self.assertEqual((pencils.after, pencils.confidence), ("Хобби", MEDIUM))
        self.assertEqual((sheets.after, sheets.confidence), ("Покупки в дом", HIGH))
        self.assertEqual((plants.after, plants.confidence), ("Покупки в дом", HIGH))
        self.assertEqual(roses.after, "Подарки")

    def test_mixed_home_carts_are_review(self):
        comments = (
            "вешалка, носочки",
            "Купили дейзик, зубную пасту и другие товары для дома.",
            "Купила стильки и шарики для тенниса",
            "Купили кубики для йоги, мячик, губки для мытья посуды и носки Лизе.",
            "полотенцее шапка резинки Семья должна Лизе",
        )
        for comment in comments:
            with self.subTest(comment=comment):
                decision = semantic_override(expense_operation("Покупки в Дом", comment))
                self.assertEqual(decision.after, "Покупки в дом")
                self.assertEqual(decision.confidence, REVIEW)

    def test_home_unknown_or_shop_only_comment_is_review(self):
        comments = ("UPDdone: долг возвращен", "Семья должна Лизе", "Доставка", "Мастер", "Тему", "Пепко", "Лилли", "Китайский", "Купили что-то для дома")
        for comment in comments:
            with self.subTest(comment=comment):
                decision = classify_home(expense_operation("Покупки в Дом", comment))
                self.assertEqual(decision.confidence, REVIEW)
        self.assertEqual(classify_home(expense_operation("Покупки в Дом", "Купил ведро для мытья полов")).confidence, HIGH)

    def test_home_specific_subjects_override_default(self):
        running = semantic_override(expense_operation("Покупки в Дом", "Купили беговую дорожку"))
        hygiene = semantic_override(expense_operation("Покупки в Дом", "Средство для гигиены"))
        oil = semantic_override(expense_operation("Покупки в Дом", "Локситан масло"))
        socks = semantic_override(expense_operation("Покупки в Дом", "Носочки"))

        self.assertEqual((running.after, running.confidence), ("Крупные покупки и обучение", REVIEW))
        self.assertEqual(hygiene.after, "Уход за собой")
        self.assertEqual(oil.after, "Уход за собой")
        self.assertEqual(socks.after, "Одежда")

    def test_personal_subscription_uses_cross_category_history(self):
        first = expense_operation("Подписки", "Подписка ChatGPT")
        personal = expense_operation("Госпожа", "Подписка на чат Джипити", row=8)
        context = build_rule_context((first, personal), {"allowed": (), "events": ()})

        decision = semantic_override(personal, context)

        self.assertEqual(decision.after, "Ежемесячные подписки")
        self.assertEqual(decision.confidence, MEDIUM)

    def test_single_personal_subscription_is_not_high_confidence_monthly(self):
        item = expense_operation("Госпожа", "Подписка неизвестного сервиса")
        context = build_rule_context((item,), {"allowed": (), "events": ()})

        decision = semantic_override(item, context)

        self.assertEqual(decision.after, "Разовые подписки")
        self.assertEqual(decision.confidence, MEDIUM)

    def test_spaced_cyrillic_vdsina_joins_recurring_series(self):
        first = expense_operation("Подписки", "VDSINA")
        second = expense_operation("Подписки", "ВД СИНА", row=8)
        context = build_rule_context((first, second), {"allowed": (), "events": ()})

        decision = classify_subscription(second, context)

        self.assertEqual(decision.after, "Ежемесячные подписки")

    def test_repeated_kling_forgotten_subscription_is_monthly(self):
        first = expense_operation("Госпожа", "Подписка Kling (забыл отменить)")
        second = expense_operation("Госпожа", "Подписка на Клинк", row=8)
        context = build_rule_context((first, second), {"allowed": (), "events": ()})

        decision = semantic_override(first, context)

        self.assertEqual((decision.after, decision.confidence), ("Ежемесячные подписки", MEDIUM))

    def test_sport_subscription_uses_subject_category(self):
        item = expense_operation("Госпожа", "Подписка Йога, личные расходы")
        context = build_rule_context((item,), {"allowed": (), "events": ()})

        self.assertEqual(semantic_override(item, context).after, "Тренажерный зал")

    def test_settings_lists_are_parsed_independently(self):
        values = ("unrelated", "Категории расходов", "Regular A", "Regular B", "", "notes", "Категории расходов", "Event A", "Event B", "")
        rows = tuple((cell(value, value),) + tuple(cell() for _ in range(7)) for value in values)
        block = GridBlock("⚙️Настройки", 1, 119, 0, rows)

        parsed = settings_expense_category_lists(block)

        self.assertEqual(parsed["regular"], ("Regular A", "Regular B"))
        self.assertEqual(parsed["events"], ("Event A", "Event B"))
        self.assertEqual(parsed["allowed"], ("Regular A", "Regular B", "Event A", "Event B"))
        self.assertEqual(parsed["header_sheet_rows"], (121, 126))

    def test_settings_parser_requires_exactly_two_headers(self):
        rows = tuple((cell(value, value),) + tuple(cell() for _ in range(7)) for value in ("Категории расходов", "A", ""))
        with self.assertRaises(PreviewError):
            settings_expense_category_lists(GridBlock("⚙️Настройки", 1, 0, 0, rows))

    def test_regression_ids_require_exact_cardinality(self):
        base = (
            expense_operation("Госпожа", "H&M", row=1),
            expense_operation("Покупки в Дом", "plants", row=2),
            expense_operation("Транспорт", "bike", row=3),
            expense_operation("Развлечения", "bike", row=4),
        )
        with_ids = tuple(
            Operation(item.sheet_row, item.cells, item.row_hash, telegram_id, f"telegram:{telegram_id}", 1)
            for item, telegram_id in zip(base, ("6827", "4914", "6524", "6521"))
        )
        decisions = (
            Decision("Одежда", "", HIGH, ""),
            Decision("Покупки в дом", "", HIGH, ""),
            Decision("Развлечения", "", HIGH, ""),
            Decision("Развлечения", "", HIGH, ""),
        )

        self.assertTrue(regression_ids_pass(with_ids, decisions))
        self.assertFalse(regression_ids_pass(with_ids + (with_ids[0],), decisions + (decisions[0],)))

    def test_runtime_artifact_validator_detects_markdown_drift(self):
        records = (
            artifact_record(1, 2, HIGH),
            artifact_record(2, 1, REVIEW),
            artifact_record(None, 0, HIGH, changed=False),
        )
        mapping = {
            "snapshot": {"finished_at": "now"},
            "audit": {"total_operations": 3, "changed_count": 2, "unchanged_count": 1, "review_count": 1},
            "category_snapshot": {"allowed_categories": ["After"]},
            "category_summary": [{"after": "After", "count": 2, "amount_eur": "30.00", "excluded_from_eur_sum": 0}],
            "pair_counts": [{"before": "Before", "after": "After", "count": 2}],
            "operations": list(records),
        }
        markdown = render_markdown(mapping)

        self.assertTrue(all(validate_artifacts(mapping, markdown).values()))
        with self.assertRaises(PreviewError):
            validate_artifacts(mapping, markdown.replace("| 2 |", "| 3 |"))

    def test_cable_routing_is_not_sanitary_pad_self_care(self):
        cable = semantic_override(expense_operation("Покупки в Дом", "Мастер Евгений - прокладка кабелей"))
        sanitary = semantic_override(expense_operation("Покупки в Дом", "Прокладки"))
        sanitary_for_liza = semantic_override(expense_operation("Покупки в Дом", "Купили Лизе прокладки"))
        sanitary_home_note = semantic_override(expense_operation("Покупки в Дом", "Прокладки, покупки в дом"))

        self.assertEqual((cable.after, cable.confidence), ("Покупки в дом", REVIEW))
        self.assertEqual((sanitary.after, sanitary.confidence), ("Уход за собой", HIGH))
        self.assertEqual((sanitary_for_liza.after, sanitary_for_liza.confidence), ("Уход за собой", HIGH))
        self.assertEqual((sanitary_home_note.after, sanitary_home_note.confidence), ("Уход за собой", HIGH))

    def test_ambiguous_gel_home_purchase_is_review(self):
        decision = semantic_override(expense_operation("Покупки в Дом", "Купили Гель, Добровель и Лизе для дома."))

        self.assertEqual((decision.after, decision.confidence), ("Покупки в дом", REVIEW))

    def test_animal_food_with_secondary_item_is_mixed_review(self):
        items = (
            expense_operation("Животные", "Корм для собаки Луны и шампунь"),
            expense_operation("Животные", "Корм Грандорф и подарок ей"),
        )
        for item in items:
            with self.subTest(comment=item.cells[9]["formattedValue"]):
                decision = classify_animal(item, rule_context(item))
                self.assertEqual(decision.after, "Корм для Лунтинка")
                self.assertEqual(decision.confidence, REVIEW)

    def test_home_mixed_care_items_are_review(self):
        body = semantic_override(expense_operation("Покупки в Дом", "Купили масло для тела и антисептик"))
        pomade = semantic_override(expense_operation("Покупки в Дом", "Купила ватную палочку с чем-то, помаду"))

        self.assertEqual((body.after, body.confidence), ("Уход за собой", REVIEW))
        self.assertEqual((pomade.after, pomade.confidence), ("Уход за собой", REVIEW))

    def test_birthday_trampoline_series_is_entertainment(self):
        room = semantic_override(expense_operation("Господин", "Заплатил за игровую комнату батуты на день рождения"))
        deposit = semantic_override(expense_operation("Господин", "Оплата депозита для дня рождения батута"))

        self.assertEqual((room.after, room.confidence), ("Развлечения", HIGH))
        self.assertEqual((deposit.after, deposit.confidence), ("Развлечения", MEDIUM))

    def test_yandex_disk_spellings_share_monthly_history(self):
        comments = ("Оплата подписки на Яндекс.Диск", "Подписка на яндекс диск", "Подписка: ядиск", "ЯДИск и обслуживание карты")
        items = tuple(expense_operation("Госпожа", comment, row=index + 7) for index, comment in enumerate(comments))
        context = build_rule_context(items, {"allowed": (), "events": ()})

        for item in items:
            with self.subTest(comment=item.cells[9]["formattedValue"]):
                decision = semantic_override(item, context)
                self.assertEqual((decision.after, decision.confidence), ("Ежемесячные подписки", MEDIUM))

    def test_apple_and_icloud_share_monthly_history(self):
        icloud = expense_operation("Подписки", "Оплата подписки на iCloud")
        apple = expense_operation("Подписки", "Apple", row=8)
        other = expense_operation("Другое", "Подписка Apple", row=9)
        event = expense_operation("Египет 2024", "Покупка игры Apple", row=10)
        items = (icloud, apple, other, event)
        context = build_rule_context(items, {"allowed": (), "events": ("Египет 2024",)})

        decisions = (
            classify_subscription(icloud, context),
            classify_subscription(apple, context),
            semantic_override(other, context),
        )

        self.assertTrue(all((decision.after, decision.confidence) == ("Ежемесячные подписки", MEDIUM) for decision in decisions))
        self.assertEqual(context.subscription_counts["apple-cloud"], 3)

    def test_subscription_context_spelling_aliases_join_history(self):
        cases = (
            ("xiaomi", "Оплата подписки на камеру к Сеоне", "Подписка на камеру к Xiaomi"),
            ("telegram", "Подписка телега премиум", "Telegram Premium"),
            ("yandex", "Подписка на Яндекс", "Яндекс Подписка"),
            ("higgsfield", "Подписка на нано-банану в Хиггсвилде", "Higgsfield"),
        )
        for service, first_comment, second_comment in cases:
            with self.subTest(service=service):
                first = expense_operation("Подписки", first_comment)
                second = expense_operation("Подписки", second_comment, row=8)
                unrelated = expense_operation("Другое", "Купил камеру Xiaomi в Яндекс Маркете", row=9)
                context = build_rule_context((first, second, unrelated), {"allowed": (), "events": ()})
                self.assertEqual(context.subscription_counts[service], 2)
                self.assertEqual(
                    (classify_subscription(first, context).after, classify_subscription(first, context).confidence),
                    ("Ежемесячные подписки", MEDIUM),
                )

    def test_ambiguous_home_comments_and_specific_care(self):
        ambiguous = ("средства для стверчи", ":0 Мячик в китайском", "done:3 Китайский", "Паста", "Икеяdone: ножки для Лизы, лампа")
        for comment in ambiguous:
            with self.subTest(comment=comment):
                self.assertEqual(classify_home(expense_operation("Покупки в Дом", comment)).confidence, REVIEW)
        moustache = semantic_override(expense_operation("Покупки в Дом", "Купили краску для усов Влада"))
        conditioner = semantic_override(expense_operation("Покупки в Дом", "Кондей для Лизы"))
        self.assertEqual((moustache.after, moustache.confidence), ("Уход за собой", HIGH))
        self.assertEqual((conditioner.after, conditioner.confidence), ("Уход за собой", REVIEW))

    def test_home_unknown_shampoo_and_hair_ties_are_review(self):
        shampoo = semantic_override(expense_operation("Покупки в Дом", "Купили шампунь и еще какую-то фиговину для Лизы"))
        ties = classify_home(expense_operation("Покупки в Дом", "done:3 Резиночки и прочее"))

        self.assertEqual((shampoo.after, shampoo.confidence), ("Уход за собой", REVIEW))
        self.assertEqual((ties.after, ties.confidence), ("Покупки в дом", REVIEW))

    def test_other_unreal_and_decor_are_review_candidates(self):
        unreal = semantic_override(expense_operation("Другое", "Unreal Engine ???"))
        decor = semantic_override(expense_operation("Другое", "Украшения"))

        self.assertEqual((unreal.after, unreal.confidence), ("Разовые подписки", REVIEW))
        self.assertEqual((decor.after, decor.confidence), ("Покупки в дом", REVIEW))

    def test_entertainment_app_subscriptions_are_reclassified(self):
        dj = semantic_override(expense_operation("Развлечения", "Подписка на DJ приложение"))
        armfight = semantic_override(expense_operation("Развлечения", "Подписка на Дэйон Лалетин армфайт"))

        self.assertEqual((dj.after, dj.confidence), ("Разовые подписки", MEDIUM))
        self.assertEqual((armfight.after, armfight.confidence), ("Разовые подписки", REVIEW))

    def test_non_event_apartments_are_lodging(self):
        comments = ("Оплата квартиры на ночь в Нови-Саде", "Квартира в Валево", "Аренда квартиры в Нови-Саде")
        for comment in comments:
            with self.subTest(comment=comment):
                decision = lodging_override("Развлечения", comment.casefold())
                self.assertEqual((decision.after, decision.confidence), ("Жилье вне дома и отели", HIGH))
        self.assertIsNone(lodging_override("Египет 2024", "квартира в каире"))

    def test_non_event_cottage_genitive_is_lodging(self):
        decision = lodging_override("Развлечения", "оплата домика в боснии")

        self.assertEqual((decision.after, decision.confidence), ("Жилье вне дома и отели", HIGH))
        self.assertIsNone(lodging_override("Предложение руки и сердца", "оплата домика-сюрприза"))

    def test_entertainment_explicit_products_and_steam_game(self):
        lemons = semantic_override(expense_operation("Развлечения", "килограмм лимонов"))
        picnic = semantic_override(expense_operation("Развлечения", "Продукты на пикник"))
        steam = semantic_override(expense_operation("Развлечения", "Покупка игры в Steam. Чейн тугеда."))

        self.assertEqual((lemons.after, lemons.confidence), ("Продукты", HIGH))
        self.assertEqual((picnic.after, picnic.confidence), ("Продукты", HIGH))
        self.assertEqual((steam.after, steam.confidence), ("Хобби", MEDIUM))

    def test_approved_glasses_override_gift_word(self):
        item = expense_operation(
            "Госпожа",
            "Подарок Лизе, очки",
            date=45556,
            amount=26240,
            currency="RSD",
        )

        decision = approved_non_event_exception(item, "Госпожа")

        self.assertEqual(decision.after, "Одежда")
        self.assertEqual(decision.rule, "approved-glasses")

    def test_user_approved_override_uses_only_stable_identity(self):
        stable_id = "telegram:4806"
        base = expense_operation("Покупки в Дом", "Пепко: свечка и миска для Луны", row=2004)
        target = Operation(base.sheet_row, base.cells, base.row_hash, "4806", stable_id, 1)
        same_row_without_identity = Operation(base.sheet_row, base.cells, base.row_hash, "9999", "telegram:9999", 1)

        decision = user_approved_stable_override(target)

        self.assertEqual((decision.after, decision.confidence), ("Покупки для Лунтинка", HIGH))
        self.assertEqual(decision.rule, "user-approved-stable-override")
        self.assertIsNone(user_approved_stable_override(same_row_without_identity))

    def test_user_approved_override_requires_exact_cardinality(self):
        stable_id = "telegram:4806"
        override = {stable_id: ("Покупки для Лунтинка", "approved")}
        base = expense_operation("Покупки в Дом", "Покупка для Луны")
        target = Operation(base.sheet_row, base.cells, base.row_hash, "4806", stable_id, 1)
        decision = Decision("Покупки для Лунтинка", "approved", HIGH, "user-approved-stable-override")

        self.assertTrue(user_approved_overrides_pass((target,), (decision,), override))
        self.assertFalse(user_approved_overrides_pass((target, target), (decision, decision), override))
        wrong = Decision("Корм для Лунтинка", "wrong", HIGH, "user-approved-stable-override")
        self.assertFalse(user_approved_overrides_pass((target,), (wrong,), override))

    def test_blank_printing_is_user_approved_other(self):
        item = expense_operation("Печать документов", "")

        decision = classify_printing(item, rule_context(item))

        self.assertEqual((decision.after, decision.confidence), ("Другое", HIGH))
        self.assertEqual(decision.rule, "printing-unspecified-approved")

    def test_explicit_printing_subject_still_routes_by_subject(self):
        cases = (
            ("Печать документов для ВНЖ", "ВНЖ ПМЖ"),
            ("Печать декларации российского ИП", "ИП в России"),
            ("Печать APR сербского ИП", "ИП в Сербии"),
            ("Печать рабочих документов для офиса", "Аренда офиса + коммуналка"),
        )
        for comment, after in cases:
            with self.subTest(comment=comment):
                decision = classify_printing(expense_operation("Печать документов", comment), rule_context())
                self.assertEqual((decision.after, decision.confidence), (after, HIGH))

    def test_parking_and_toll_use_renamed_category(self):
        parking = semantic_override(expense_operation("Госпожа", "Парковка в аэропорту"))
        car_toll = classify_car(expense_operation("Машина", "Платная дорога"))
        transport_toll = classify_transport(expense_operation("Транспорт", "Оплата платной дороги"))

        self.assertEqual(PARKING_TOLL_CATEGORY, "Парковка и платная дорога")
        for decision in (parking, car_toll, transport_toll):
            self.assertEqual((decision.after, decision.confidence), (PARKING_TOLL_CATEGORY, HIGH))


if __name__ == "__main__":
    unittest.main()

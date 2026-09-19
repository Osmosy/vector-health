---
name: abdominal-ct-findings
description: Таксономия находок КТ брюшной полости (146 находок × 18 органов) с русскими, английскими и китайскими названиями, плюс методика замера качества модели на внешнем тесте. Источник — RADAR (Alibaba DAMO Academy, Science 2026, Apache-2.0). Use when naming/labelling abdominal CT findings, building a report checklist, or measuring an imaging model's quality.
version: 1.0.0
author: Osmosy
license: MIT
metadata:
  hermes:
    tags: [ct, abdominal, radiology, taxonomy, imaging, quality-metrics, radar]
    category: medical-imaging
---

# Находки КТ брюшной полости — таксономия и методика замера

Две вещи, которых обычно не хватает при работе с КТ брюшной полости:
**согласованный список находок** (146 позиций по 18 органам, с названиями на трёх
языках) и **методика честного замера** качества модели на внешнем тесте.

Источник таксономии — открытая модель RADAR (Alibaba DAMO Academy, статья в
Science, код Apache-2.0). Таксономия взята из её публичного CSV-вывода, тексты
апстрима не изменялись; переводы на русский — этого репозитория.

## When to Use

- Нужно назвать/разметить находку на КТ брюшной полости — берёте формулировку из таблицы.
- Строите чек-лист описания или структуру отчёта: 18 органов и их находки.
- Сопоставляете вывод модели с её же классами (китайские ключи CSV → понятное название).
- Собираете замер качества модели: как считать (внешний тест, по каждому классу) — `references/quality-metrics.md`.
- НЕ для: постановки диагноза. Таблица — это словарь классов, а не интерпретация снимка.

## Что это не заменяет

Список находок ≠ заключение. Находка в списке — это то, что модель умеет
*помечать*, а не то, что она подтверждает. Формулировка вывода и клиническое
решение остаются за врачом-рентгенологом.

## Органы и объём

| # | Орган (RU) | Organ (EN) | Оригинал (ZH) | Находок |
|---|---|---|---|---|
| 1 | Аорта | Aorta | 主动脉 | 4 |
| 2 | Двенадцатиперстная кишка | Duodenum | 十二指肠 | 5 |
| 3 | Ободочная кишка | Large bowel | 大肠 | 18 |
| 4 | Тонкая кишка | Small bowel | 小肠 | 13 |
| 5 | Сердце | Heart | 心脏 | 2 |
| 6 | Рёбра | Rib | 肋骨 | 3 |
| 7 | Печень | Liver | 肝 | 18 |
| 8 | Лёгкие | Lung | 肺 | 10 |
| 9 | Почки | Kidney | 肾 | 14 |
| 10 | Надпочечники | Adrenal gland | 肾上腺 | 6 |
| 11 | Желудок | Stomach | 胃 | 6 |
| 12 | Жёлчный пузырь и жёлчные протоки | Gallbladder / extrahepatic bile ducts | 胆囊 | 14 |
| 13 | Поджелудочная железа | Pancreas | 胰腺 | 10 |
| 14 | Селезёнка | Spleen | 脾 | 8 |
| 15 | Мочевой пузырь | Bladder | 膀胱 | 6 |
| 16 | Воротная вена | Portal vein | 门静脉 | 3 |
| 17 | Пищевод | Esophagus | 食管 | 5 |
| 18 | Крестец | Sacrum | 骶骨 | 1 |
| | **Итого** | | | **146** |

## Полная таблица находок

Машиночитаемая версия — `references/radar-taxonomy.json` (поля `*_zh` — оригинал
апстрима, `*_ru` — перевод; не переименовывать китайские ключи: по ним
сопоставляется CSV модели).


### Аорта — Aorta (主动脉) — 4 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Расслоение аорты | Aortic dissection | 主动脉夹层 |
| Аневризма аорты | Aortic aneurysm | 主动脉瘤 |
| Атеросклероз аорты | Atherosclerosis | 粥样硬化 |
| Кальциноз аорты | Calcification | 钙化 |

### Двенадцатиперстная кишка — Duodenum (十二指肠) — 5 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Объёмное образование | Mass | 占位 |
| Мешковидное выпячивание | Saccular outpouching | 囊袋状突出影 |
| Дивертикул | Diverticulum | 憩室 |
| Обструкция | Obstruction | 梗阻 |
| Язва | Ulcer | 溃疡 |

### Ободочная кишка — Large bowel (大肠) — 18 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Болезнь Крона | Crohn's disease | 克罗恩病 |
| Кальциноз стенки кишки | Mural calcification | 大肠（壁）钙化 |
| Колит (острый и хронический) | Colitis | 急慢性（结）肠炎 |
| Неровность серозной поверхности | Serosal surface irregularity | 浆膜面毛糙 |
| Язвенный колит | Ulcerative colitis | 溃疡性结肠炎 |
| Рак прямой кишки | Rectal cancer | 直肠癌 |
| Скопление газа и жидкости | Gas and fluid accumulation | 积液积气 |
| Рак ободочной кишки | Colon cancer | 结肠癌 |
| Неровность стенки | Wall irregularity | 肠壁毛糙 |
| Отёк стенки | Wall edema | 肠壁水肿 |
| Инвагинация | Intussusception | 肠套叠 |
| Дивертикул | Diverticulum | 肠憩室 |
| Кишечная непроходимость | Obstruction | 肠梗阻 |
| Перфорация | Perforation | 肠穿孔 |
| Расширение кишки | Dilatation | 肠道扩张 |
| Смазанность жировых промежутков | Blurring of fat planes | 脂肪间隙模糊 |
| Аппендицит | Appendicitis | 阑尾炎 |
| Аппендиколит (копролит) | Appendicolith | 阑尾粪石 |

### Тонкая кишка — Small bowel (小肠) — 13 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Болезнь Крона | Crohn's disease | 克罗恩病 |
| Инвагинация | Intussusception | 套叠 |
| Заворот | Volvulus | 扭转 |
| Обструкция | Obstruction | 梗阻 |
| Лимфома | Lymphoma | 淋巴瘤 |
| Скопление газа и жидкости | Gas and fluid accumulation | 积气积液 |
| Панникулит брыжейки | Mesenteric panniculitis | 系膜指膜炎 |
| Увеличение брыжеечных лимфоузлов | Mesenteric lymphadenopathy | 系膜淋巴结肿大 |
| Утолщение стенки | Wall thickening | 肠壁增厚 |
| Расширение кишки | Dilatation | 肠管扩张 |
| Липома | Lipoma | 脂肪瘤 |
| Гастроинтестинальная стромальная опухоль (GIST) | Gastrointestinal stromal tumor | 间质瘤（胃肠间质瘤-gist） |
| Энтерит (острый и хронический) | Enteritis | （急慢性）小肠炎 |

### Сердце — Heart (心脏) — 2 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Выпот в перикарде | Pericardial effusion | 心包积液 |
| Кардиомегалия | Cardiomegaly | 心影（脏）增大 |

### Рёбра — Rib (肋骨) — 3 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Метастаз (в т.ч. костный при раке молочной железы) | Metastasis | 转移瘤（乳腺癌 骨转移） |
| Перелом | Fracture | 骨折 |
| Деструкция костной ткани | Bone destruction | 骨质破坏 |

### Печень — Liver (肝) — 18 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Гиподенсный очаг | Hypoattenuating lesion | 低密度影 |
| Перипортальный отёк (отёк вокруг глиссоновой капсулы) | Periportal edema | 格林森鞘积液 |
| Диспропорция объёма долей | Lobar volume disproportion | 比例失调 |
| Волнистость контура | Undulating contour | 波浪状改变 |
| Цирроз | Cirrhosis | 硬化 |
| Узловое накопление контраста | Nodular enhancement | 结节状强化 |
| Расширение внутрипечёночных желчных протоков | Intrahepatic bile duct dilatation | 肝内胆管扩张 |
| Внутрипечёночный холелитиаз | Hepatolithiasis | 肝内胆管结石 |
| Внутрипечёночные кальцинаты | Intrahepatic calcification | 肝内钙化灶 |
| Киста печени | Cyst | 肝囊肿 |
| Гепатоцеллюлярная карцинома | Hepatocellular carcinoma | 肝细胞癌 |
| Гиперденсный очаг во внутрипечёночных жёлчных протоках | Hyperattenuating lesion in intrahepatic bile ducts | 肝胆管内高密度影 |
| Гемангиома печени | Hemangioma | 肝血管瘤 |
| Внутрипечёночная холангиокарцинома | Intrahepatic cholangiocarcinoma | 胆管癌 |
| Стеатоз печени | Steatotic liver disease | 脂肪肝 |
| Абсцесс | Abscess | 脓肿 |
| Метастаз | Metastasis | 转移瘤 |
| Неровность края | Irregular margin | 边缘不规则 |

### Лёгкие — Lung (肺) — 10 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Очаговое затемнение (пятнистое) | Patchy opacity | 斑片影 |
| Пневмоторакс | Pneumothorax | 气胸 |
| Узел | Nodule | 结节 |
| Объёмное образование | Mass | 肺占位 |
| Коллапс лёгкого | Pulmonary collapse | 肺萎陷 |
| Плевральный выпот | Pleural effusion | 胸腔积液 |
| Ателектаз | Atelectasis | 膨胀不全 |
| Метастаз | Metastasis | 转移瘤 |
| Кальцинат | Calcification | 钙化灶 |
| Гиперденсное затемнение | Hyperattenuating opacity | 高密度影 |

### Почки — Kidney (肾) — 14 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Гиподенсный очаг | Hypoattenuating lesion | 低密度影 |
| Киста | Cyst | 囊肿 |
| Поликистоз почек | Polycystic kidney disease | 多囊肾 |
| Истончение паренхимы | Parenchymal thinning | 实质变薄 |
| Неусиливающийся кистозный очаг | Nonenhancing cystic lesion | 无强化囊性灶 |
| Аневризма почечной артерии | Renal artery aneurysm | 肾动脉瘤 |
| Расширение почечной лоханки | Renal pelvic dilatation | 肾盂扩张 |
| Рак почечной лоханки | Renal pelvic cancer | 肾盂癌 |
| Гидронефроз | Hydronephrosis | 肾盂积水 |
| Почечно-клеточный рак (светлоклеточный) | Renal cell carcinoma | 肾细胞癌（透明细胞癌） |
| Атрофия почки | Atrophy | 肾萎缩 |
| Ангиомиолипома | Angiomyolipoma | 肾血管平滑肌脂肪瘤 |
| Нефролитиаз (камни почек/лоханки) | Nephrolithiasis | 肾（盂）结石 |
| Гиперденсный очаг | Hyperattenuating lesion | 高密度影 |

### Надпочечники — Adrenal gland (肾上腺) — 6 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Гиперплазия | Hyperplasia | 增生 |
| Узел | Nodule | 结节 |
| Липома | Lipoma | 脂肪瘤 |
| Аденома | Adenoma | 腺瘤 |
| Метастаз | Metastasis | 转移瘤 |
| Кальцинат | Calcification | 钙化 |

### Желудок — Stomach (胃) — 6 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Отёк стенки | Wall edema | 壁水肿 |
| Расширение | Dilatation | 扩张 |
| Варикоз вен дна желудка | Gastric fundal varices | 胃底静脉曲张 |
| Язва желудка | Ulcer | 胃溃疡 |
| Рак желудка | Gastric cancer | 胃癌 |
| Гастроинтестинальная стромальная опухоль (GIST) | Gastrointestinal stromal tumor (GIST) | 间质瘤（gist） |

### Жёлчный пузырь и жёлчные протоки — Gallbladder / extrahepatic bile ducts (胆囊) — 14 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Желчнокаменная болезнь | Cholecystolithiasis | 结石 |
| Узловой камнеподобный гиперденсный очаг | Nodular stone-like hyperattenuating lesion | 结节状致密影 |
| Увеличение желчного пузыря | Distention | 胆囊增大 |
| Холецистит | Cholecystitis | 胆囊炎 |
| Рак желчного пузыря | Gallbladder cancer | 胆囊癌 |
| Аденомиоматоз | Adenomyomatosis | 胆囊腺肌症 |
| Утолщение стенки внепечёночных жёлчных протоков | Extrahepatic bile duct wall thickening | 胆管壁增厚 |
| Расширение внепечёночных жёлчных протоков | Extrahepatic bile duct dilatation | 胆管扩张 |
| Холангит | Cholangitis | 胆管炎 |
| Холангиокарцинома | Cholangiocarcinoma | 胆管癌 |
| Пневмобилия (газ в жёлчных путях) | Pneumobilia | 胆管积气 |
| Камень внепечёночных жёлчных протоков | Extrahepatic bile duct stone | 胆管结石 |
| Гиперденсный очаг | Hyperattenuating lesion | 高密度影 |
| Ксантогранулёма | Xanthogranuloma | 黄色肉芽肿 |

### Поджелудочная железа — Pancreas (胰腺) — 10 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Гиподенсный очаг | Low-density lesion | 低密度影 |
| Киста | Cyst | 囊肿 |
| Смазанность парапанкреатической клетчатки | Blurring of peripancreatic fat planes | 围脂肪间隙模糊 |
| Опухоль / рак поджелудочной железы | Pancreatic cancer | 肿瘤或胰腺癌 |
| Парапанкреатическая псевдокиста | Peripancreatic pseudocyst | 胰周假性囊肿 |
| Расширение панкреатического протока | Pancreatic duct dilatation | 胰管扩张 |
| Конкремент панкреатического протока | Pancreatic duct calculus | 胰管结石 |
| Панкреатит | Pancreatitis | 胰腺炎 |
| Увеличение поджелудочной железы | Enlargement | 胰腺饱满 |
| Атрофия | Atrophy | 萎缩 |

### Селезёнка — Spleen (脾) — 8 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Гиподенсный очаг | Hypoattenuating lesion | 低密度灶 |
| Добавочная селезёнка | Accessory spleen | 副脾 |
| Киста | Cyst | 囊肿 |
| Инфаркт | Infarction | 梗死 |
| Очаговый гиподенсный участок | Patchy hypoattenuating lesion | 片状低密度区 |
| Спленомегалия | Splenomegaly | 脾大 |
| Лимфома селезёнки | Lymphoma | 脾脏淋巴瘤 |
| Кальцинат | Calcification | 钙化 |

### Мочевой пузырь — Bladder (膀胱) — 6 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Дивертикул | Diverticulum | 憩室 |
| Камень | Stone | 结石 |
| Неровность стенки | Wall irregularity | 膀胱壁毛糙 |
| Цистит | Cystitis | 膀胱炎 |
| Рак мочевого пузыря | Bladder cancer | 膀胱癌 |
| Очаг мягкотканной плотности | Soft-tissue attenuation lesion | 软组织密度影 |

### Воротная вена — Portal vein (门静脉) — 3 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Расширение | Dilatation | 增宽 |
| Тромбоз | Thrombosis | 栓塞 |
| Портальная гипертензия | Hypertension | 高压 |

### Пищевод — Esophagus (食管) — 5 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Расширенные извитые трубчатые тени (сосуды) | Dilated and tortuous tubular opacities | 增粗迂曲血管影 |
| Утолщение стенки | Wall thickening | 管壁增厚 |
| Грыжа пищеводного отверстия диафрагмы | Hiatal hernia | 裂孔疝 |
| Расширенные извитые вены | Dilated and tortuous veins | 静脉扩张迂曲 |
| Варикозное расширение вен | Varices | 静脉曲张 |

### Крестец — Sacrum (骶骨) — 1 находок

| Находка (RU) | Finding (EN) | Оригинал (ZH) |
|---|---|---|
| Остеит | Osteitis | 骨炎 |

## Ключевые решения и грабли

- **Китайские ключи не переводить.** Оригинал лежит в поле `finding_zh` /
  `organ_zh` и повторяется в `csv_column_zh_en`. Это не «лишний текст», а ключ
  сопоставления с выводом модели: переименуете — потеряете связь с CSV.
- **«Находка» ≠ «болезнь».** В списке есть признаки, а не диагнозы: затемнение
  жировой клетчатки, неровность контура, гиподенсный очаг. Классификация
  «что это за болезнь» — отдельная задача.
- **Одинаковые названия у разных органов — норма.** «Киста» есть у печени, почек,
  селезёнки и поджелудочной; «метастаз» — у печени, лёгких, надпочечников и рёбер.
  Различает их именно орган, поэтому в отчёте всегда указывайте орган.
- **Опечатка апстрима остаётся видимой.** В исходном заголовке для GIST желудка
  есть вложенные скобки — в таблице он разобран на три поля, а исходная строка
  сохранена в `csv_column_zh_en` без правок.

## Что мерить при работе с моделью

Коротко: AUC по каждому классу отдельно, а не одно среднее по всем. Методика,
цифры открытой модели RADAR и разбор типовых ошибок — `references/quality-metrics.md`.

## Источник и лицензия

Таксономия: [alibaba-damo-academy/damo-radar](https://github.com/alibaba-damo-academy/damo-radar),
файл `results/RADAR_infer_results_demo.csv` — Apache-2.0 (© Alibaba DAMO Academy).
**Веса модели — другая лицензия:** CC BY-NC-SA 4.0 (некоммерческая), см. `NOTICE.md`.
Переводы и текст навыка — MIT (© Osmosy); китайские и английские названия взяты
из источника без изменений.

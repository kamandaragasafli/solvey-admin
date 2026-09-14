"""
Bu modul hesabatın sütun strukturunu (şəhər qrupları və rəngləri) təsvir edir.
Excel şablonundakı (Ağcabədi -> Şirvan) qruplaşdırma və rənglər burada saxlanılır ki,
həm parser (Bakı+Abşeron birləşdirmə, adların normallaşdırılması), həm də şablon
(HTML/CSS-də başlıq rənglərini göstərmək üçün) eyni mənbəni istifadə etsin.
"""

# (rəng_hex, [şəhərlər]) — sıra Excel şablonundakı sıra ilə eynidir
CITY_GROUPS = [
    ("FFFF00", ["Ağcabədi", "Ağdam", "Bərdə", "Tərtər"]),
    ("92D050", ["Gəncə", "Şəmkir", "Goranboy"]),
    ("00B0F0", ["Mingəçevir", "Ağdaş", "Yevlax"]),
    ("C00000", ["Beyləqan", "Fizuli", "İmişli"]),
    ("F4B7C6", ["Lənkəran", "Astara", "Lerik"]),
    ("F2CEA2", ["Göyçay", "Ucar", "Zərdab"]),
    ("FF0000", ["Balakən", "Qax", "Şəki", "Zaqatala"]),
    ("F2CEA2", ["İsmayıllı", "Oğuz", "Qəbələ"]),
    ("FBE5D6", ["Quba", "Qusar", "Xaçmaz", "Xudat"]),
    ("C00000", ["Kürdəmir", "Ağsu", "Şamaxı", "Qobustan"]),
    ("2E75B6", ["Hacıqabul", "Neftçala", "Salyan", "Şirvan"]),
]

# Bütün "rəsmi" şəhərlərin sırası ilə düz siyahısı (Bakı+Abşeron xaric)
REFERENCE_CITIES = [city for _, cities in CITY_GROUPS for city in cities]

# Hər şəhərin hansı qrup rənginə aid olduğunu tez tapmaq üçün
CITY_COLOR = {city: color for color, cities in CITY_GROUPS for city in cities}

# Excel mənbəyində fərqli yazılan, amma eyni şəhəri bildirən adlar
CITY_NAME_ALIASES = {
    "Füzuli": "Fizuli",
}

# Bakı və Abşeron bir sütunda birləşdirilir
MERGED_BAKU_COLUMN = "Bakı+Abşeron"
BAKU_SOURCE_KEYS = ["Bakı", "Abşeron"]

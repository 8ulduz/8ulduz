# Bu repoda işləyən agentlər üçün

Saytın iki dəyişməz qırmızı xətti var: [docs/qirmizi-xetler.md](docs/qirmizi-xetler.md). Dəyişiklikdən əvvəl oxuyun.

1. Xəbər ən geci 60 saniyədən bir yenilənir, axın dayanmır. Sürətli dövrəyə şəbəkə sorğusu və ya ağır iş əlavə etməyin; onlar `slow_cycle`-a gedir.
2. Xarici mənbələrdən Azərbaycan və rəhbərliyi haqqında, müxalifət mənbələrindən xəbər düşmür. Lentə yazan hər yol `content_policy.enforce`-dan keçməlidir.

`tests/test_red_lines.py` və ya `bir-deqiqe` işi düşürsə, testi yumşaltmayın, dəyişikliyi düzəldin. Qaydanı yalnız sayt sahibi dəyişə bilər, onun açıq göstərişi olmadan dəyişməyin.

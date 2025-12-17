# Referencia de Items por Área

Este documento lista todos los items que deberían estar disponibles en cada área según la organización actual.

## 📋 Nota Importante

Los items se obtienen directamente de MRPeasy API. Para que estos items aparezcan correctamente:
1. Deben existir en MRPeasy con el código correspondiente
2. Deben tener `is_raw = False` (no ser materias primas)
3. Deben tener el campo `custom_44680` configurado con el nombre del equipo correspondiente
4. Deben tener el campo `group_title` configurado con la categoría correspondiente

---

## JORGE TEAM (Preparation Bases)

### Items que deberían estar en esta área:

- A1233 - Eggplant - Grilled
- A1635 - Bamia Base - bag
- A1615 - Chickpea - Cooked - For Garnish - Bag
- A1619 - Octopus - Cooked - bag
- A1861 - Beef Chuck Flap Boneless - Cooked - Bag
- A1639 - Duck - Cooked - bag
- A1574 - Yalanji - Cooked - Sous Vide - Bag
- A1490 - Lamb - Shoulder - Sous Vide - Cooked - Bag
- A1634 - Friki Base - bag
- A1600 - Moujaddara Base - bag
- A1942 - Lamb - Shanks - Sous Vide - Cooked - Bag
- A1631 - Lamb Kawarma Mix - Ground - bag
- A1315 - Cornstarch - Cooked
- A1691 - Bamia - To Reheat - case
- A1693 - Friki - To Reheat - case
- A1696 - Moujaddara - To Reheat - case
- A1646 - Sugar Syrup - bag
- A1640 - Shish Borek Sauce - bag
- A1176 - Lamb Stock - Secondary Item - bag
- A1903 - Lamb Tongue - Cooked - Bag
- A1011 - Yalanji Base
- A1650 - Tomato Sauce - bag
- A1641 - Tajin - bag

---

## ALEJANDRO TEAM (Dips and Sauces)

### Items que deberían estar en esta área:

- A1564 - Eggplant Mutabbal - Bag
- A1563 - Beet Mutabbal - Bag
- A1566 - Mouhammara - Bag
- A1549 - Garlic Yogourt - Bag - Bulk
- A1280 - Lemon Garlic Sauce
- A1612 - Marinade - Lamb - bag
- A1545 - Tarator - Bag
- A1575 - Marinade - Chicken - bag
- A1550 - Garlic Mayo - Bag - Bulk
- A1565 - Hummus - Bag
- A1616 - Falafel base - bag
- A1649 - Beet - Steamed - bag
- A1544 - Tahini Yogourt - Bag
- A1871 - Ketchup Sauce for Shish Taouk

---

## ASSEMBLY TEAM (Kits)

### Items que deberían estar en esta área:

- A1689 - Mouhammara Kit - case
- A1684 - Beet Mutabbal Kit - case
- A1685 - Eggplant Mutabbal Kit - case
- A1026 - Labneh - Bulk - bag
- A1688 - Labneh Kit - case
- A1737 - Marinated Cucumbers - Pickles - Cut
- A1686 - Hummus Kit - case
- A1629 - Falafel - Not Cooked - Frozen - Bag
- A1385 - Fried Pita - Spices - Bulk
- A1678 - Purslane - Cut

---

## SAMIA TEAM (Dessert)

### Items que deberían estar en esta área:

- A1567 - Cheese Borek - tray
- A1568 - Shish Borek - tray
- A1606 - Kataifi Nests - tray
- A1652 - Cheese Mix - Borek - tray
- A1604 - Ice Cream - Pistachio - tray
- A1017 - Kunafa - Individual Portion - Frozen
- A1015 - Ice Cream - Chocolate
- A1602 - Dough - Shish Borek - tray
- A1603 - Dough - Cheese Borek - tray
- A1633 - Safarjal - half pan (2.5 kg)

---

## RAWAD TEAM (Others)

### Items que deberían estar en esta área:

- A1876 - Salmon Filet - Bag - Raw - Marinated
- A1935 - Cookie - Pistachio Baklava - Frozen - bag
- A1925 - Cookie - Halva Sesame - Frozen - bag
- A1628 - Pistachio Kibbeh - Cooked - Frozen - Bag
- A1553 - Confit Tomatoes - Bag - Bulk
- A1907 - Potato Spices Mix

---

## THEODORA TEAM (Appetizers)

### Items que deberían estar en esta área:

- A1632 - Pistachio Kibbeh - Not Cooked - Frozen - tray
- A1613 - Shrimp Kataifi - Raw - Frozen - tray
- A1607 - Yalanji - Frozen - Not Cooked - bag

---

## BUTCHER TEAM (Raw proteins)

### Items que deberían estar en esta área:

- A1499 - Kabab Meat Mix
- A1614 - Kibbeh Naye - raw - frozen - bag
- A1547 - Lamb Shawarma - Leg - Bag - Raw - Marinated
- A1543 - Chicken Shish Taouk - Bag - Raw - Marinated
- A1647 - Lamb - Ground - bag

---

## GRILL TEAM (To re heat)

### Items que deberían estar en esta área:

- A1049 - Cherry Sauce - bag
- A1653 - Kabab - Raw - bag
- A1697 - Shish Taouk - To Reheat - case
- A1720 - Red Oil
- A1452 - Green Sauce
- A1698 - Kabab - To Reheat - case
- A1694 - Halloumi - To Reheat - case
- A1692 - Cherry Kabab - To Reheat - case
- A1690 - Grilled Octopus - To Reheat - case
- A1551 - Terbyelli - bag
- A1643 - Dukka - bag

---

## BREAD TEAM

### Items que deberían estar en esta área:

- A1558 - Saj Bread - Small - Bag of 24 units
- A1561 - Saj Bread Dough - Small Ball - Tray of 24

---

## ⚠️ Configuración Requerida en MRPeasy

Para que estos items aparezcan correctamente en la aplicación, cada item debe tener:

1. **custom_44680** configurado con el nombre del equipo:
   - "Jorge Team" para Preparation Bases
   - "Alejandro Team" para Dips and Sauces
   - "Assembly Team" para Kits
   - "Samia Team" para Dessert
   - "Rawad" para Others
   - "Theadora Team" para Appetizers
   - "Butcher Team" para Raw proteins
   - "Grill Team" para To re heat
   - "Bread Team" para Bread items

2. **group_title** configurado con la categoría correspondiente (esto determina qué categorías aparecen en Step 2)

3. **is_raw = False** para que aparezcan en la lista

---

## 🔍 Verificación

Para verificar que los items estén correctamente configurados:
1. Revisa en MRPeasy que cada item tenga el código correcto
2. Verifica que `custom_44680` coincida con el equipo
3. Verifica que `group_title` esté configurado
4. Asegúrate de que `is_raw = False`


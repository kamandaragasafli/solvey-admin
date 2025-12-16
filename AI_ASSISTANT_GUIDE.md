# AI Assistant Database Query Guide

The AI assistant can now query your database and provide real-time information. Here are some example queries you can try:

## 📋 Available Queries

### Doctor Queries

1. **Recent Doctors**
   - "Ən son əlavə olunan həkimləri göstər"
   - "Son 5 həkim kimdir?"
   - "Yeni əlavə olunan həkimləri göstər"

2. **Doctor Statistics**
   - "Həkim statistikalarını göstər"
   - "Neçə həkim var?"
   - "Bu ay neçə həkim əlavə olunub?"
   - "Dərəcə üzrə həkim paylanması"

3. **Search Doctors**
   - "Bakı bölgəsinin həkimlərini tap"
   - "Ahmed adlı həkimləri tap"
   - "AB-12345 barkodlu həkim"

4. **Doctors by Region**
   - "Bakı bölgəsinin həkimlərini göstər"
   - "Sumqayıt bölgəsinin həkimləri"

### Region Queries

1. **Region Statistics**
   - "Bölgə statistikalarını göstər"
   - "Bütün bölgələrin məlumatlarını ver"
   - "Hər bölgədə neçə həkim var?"

### Financial Queries

1. **Financial Summary**
   - "Maliyyə ümumi məlumatları"
   - "Ümumi borc nə qədərdir?"
   - "Neçə həkim borcludur?"

## 💡 Example Conversations

**User:** "Ən son əlavə olunan 5 həkimi göstər"

**AI:** 
```
Ən son əlavə olunan həkimlər:

1. Dr. Əhməd Məmmədov (BA-12345)
   Bölgə: Bakı, Şəhər: Bakı
   Klinika: Klinika 1, İxtisas: CA
   Dərəcə: I Dərəcə, Tarix: 2025-01-15 10:30

2. Dr. Ayşə Quliyeva (BA-12346)
   ...
```

**User:** "Həkim statistikalarını göstər"

**AI:**
```
📊 Həkim Statistikaları:

Ümumi həkim sayı: 150
Bu ay əlavə olunan: 12

Dərəcə üzrə:
  - I Dərəcə: 45
  - II Dərəcə: 80
  - III Dərəcə: 25

Bölgə üzrə (top 5):
  - Bakı: 60
  - Sumqayıt: 30
  ...
```

## 🔒 Security

- All database queries are read-only
- No data modification functions are exposed
- Queries are limited to prevent performance issues
- Only authenticated users can access the AI assistant

## 🚀 How It Works

The AI uses OpenAI's function calling feature to:
1. Understand your natural language query
2. Determine which database function to call
3. Execute the query safely
4. Format and present the results in a user-friendly way

## 📝 Notes

- The AI understands queries in Azerbaijani language
- You can ask questions naturally - no need for specific syntax
- Results are formatted for easy reading
- The AI maintains conversation context for follow-up questions


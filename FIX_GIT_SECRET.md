# GitHub Secret Scanning Problemi - Həll Təlimatı

## Problem
GitHub secret scanning `.env` faylında OpenAI API Key tapıb push-u bloklayır. Bu təhlükəsizlik riskidir.

## Həll Addımları

### 1. `.env` faylını git-dən çıxarın
```bash
cd c:\Users\User\Desktop\Solvey-admin
git rm --cached config/.env
```

### 2. Commit edin
```bash
git add config/.gitignore
git commit -m "Remove .env from git tracking"
```

### 3. Git history-dən `.env` faylını silin (vacibdir!)

**Seçim 1: Git filter-branch (tövsiyə olunur)**
```bash
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch config/.env" --prune-empty --tag-name-filter cat -- --all
```

**Seçim 2: BFG Repo-Cleaner (daha sürətli)**
```bash
# BFG yükləyin: https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --delete-files .env
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### 4. Force push edin (diqqətli olun!)
```bash
git push origin --force --all
```

### 5. API Key-i dəyişdirin (vacibdir!)
`.env` faylındakı `OPENAI_API_KEY` artıq exposed olub. Yeni key yaradın:
- https://platform.openai.com/api-keys
- Köhnə key-i silin və yenisini yaradın
- `.env` faylında yeniləyin

### 6. `.env.example` faylı yaradın (tövsiyə olunur)
```bash
# .env.example faylı yaradın (API key olmadan)
cp config/.env config/.env.example
# Sonra .env.example-da API key-i silin və placeholder qoyun:
# OPENAI_API_KEY=your_api_key_here
```

## Qeyd
- Git history-dən `.env` faylını silmədən push etmək təhlükəsizdir, amma secret hələ də history-də qalacaq
- Force push etmədən əvvəl bütün branch-ləri backup edin
- API key-i dərhal dəyişdirin çünki artıq exposed olub

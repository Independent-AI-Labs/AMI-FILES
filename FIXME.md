# CRITICAL MODULE FIX INSTRUCTIONS

## YOUR MISSION:
Fix ALL issues in FILES module and push with ALL checks passing. NO CHEATING.

---

### STEP 1: GO TO MODULE
```bash
cd files
pwd
```

### STEP 2: FIX MYPY.INI 
**THE MOST CRITICAL ISSUE: mypy.ini has `files = backend/` which ONLY checks backend folder**
```bash
# Read current mypy.ini
cat mypy.ini

# Edit mypy.ini and REMOVE the line "files = backend/" completely
# This makes mypy scan EVERYTHING
```

### STEP 3: RUN RUFF AND FIX ALL
```bash
# Auto-fix what's possible
../.venv/Scripts/ruff check . --fix

# Check what remains
../.venv/Scripts/ruff check .

# Fix remaining issues manually - NO SUPPRESSION
```

### STEP 4: RUN MYPY AND FIX ALL
```bash
# Run mypy on ENTIRE module
../.venv/Scripts/python -m mypy . --show-error-codes

# Fix EVERY type error - NO "type: ignore"
```

### STEP 5: RUN TESTS AND FIX ALL
```bash
# Run all tests
../.venv/Scripts/python -m pytest tests/ -v --tb=short

# Fix EVERY failing test - NO "pytest.skip"
```

### STEP 6: RUN PRE-COMMIT
```bash
# Run all pre-commit hooks
../.venv/Scripts/pre-commit run --all-files

# If anything fails, fix and re-run
```

### STEP 7: FINAL VERIFICATION
```bash
# ALL must pass:
../.venv/Scripts/ruff check .
../.venv/Scripts/python -m mypy . --show-error-codes  
../.venv/Scripts/python -m pytest tests/ -v
../.venv/Scripts/pre-commit run --all-files
```

### STEP 8: COMMIT AND PUSH
```bash
git add -A
git commit -m "fix: Complete FILES module code quality overhaul"
# NO --no-verify EVER

git push origin HEAD
# Use 600000ms (10 minute) timeout for push
```

---

## ABSOLUTE RULES:
1. **REMOVE `files = backend/` from mypy.ini** - MUST scan entire module
2. **ZERO ruff violations**
3. **ZERO mypy errors**  
4. **ALL tests pass**
5. **ALL pre-commit hooks pass**
6. **NO --no-verify**
7. **NO type: ignore**
8. **NO # noqa**
9. **NO pytest.skip**
10. **FIX ACTUAL PROBLEMS, not symptoms**

---

## IF YOU FAIL ANY CHECK:
**STOP. FIX IT. DON'T PROCEED.**

## SPECIFIC FILES MODULE ISSUES:
- Remove "files = backend/" from mypy.ini
- Check file operation permissions
- Verify path handling works correctly
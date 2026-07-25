.PHONY: mypy ruff ruff-format

mypy:
	mypy --check-untyped-defs zsh_favorite_dir.py

ruff:
	# Target really is 3.3
	ruff check --target-version py37 --extend-ignore UP032 zsh_favorite_dir.py

ruff-format:
	ruff format --target-version py37 zsh_favorite_dir.py

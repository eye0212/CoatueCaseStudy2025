
.PHONY: install init daily export plot

install:
	pip install -r requirements.txt

init:
	python -m reddit_pitch.cli init-db

daily:
	python -m reddit_pitch.cli daily-all

export:
	python -m reddit_pitch.cli export-csv

plot:
	python -m reddit_pitch.cli plot

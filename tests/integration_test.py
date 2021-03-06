import json
import pytest

from src.models import Official
from src.server import app

with open('tests/support/sample_text.txt') as f:
    SAMPLE_TEXT = f.read()


class TestIntegration:

    def test_extract_returns_relevant_data(self):
        with open('tests/support/sample_article.html') as f:
            html = f.read()
        data = json.dumps({'html': html})
        _, response = app.test_client.post('/parse_article', data=data)

        expected_title = 'Net Neutrality Supporters Launch New Campaign To '\
            'Reverse Unpopular FCC Decision'
        assert response.status == 200
        assert response.json.get('title') == expected_title
        assert 'Ryan Grenoble' in response.json.get('authors')
        assert response.json.get('date_published')
        assert response.json.get('text')
        assert response.json.get('top_image_url')

    def test_classify_returns_unknown_when_text_does_not_match(self):
        data = json.dumps({'text': 'hey there'})
        _, response = app.test_client.post('/classify', data=data)
        assert response.status == 200
        assert response.json.get('classification') is None

    def test_classify_returns_political_when_text_contains_name_of_official(self):
        Official.create(first_name='Reid', last_name='Ribble',
                        mv_key='reid-ribble')
        data = json.dumps({'text': 'When Reid Ribble started...'})
        _, response = app.test_client.post('/classify', data=data)
        assert response.status == 200
        assert response.json.get('classification') == 'political'
        Official.delete().execute()

    def test_analyze_calculates_text_read_time_in_minutes_rounded_up(self):
        data = json.dumps({'text': SAMPLE_TEXT})
        _, response = app.test_client.post('/analyze', data=data)
        assert response.status == 200
        assert response.json.get('read_time') == 2

    def test_analyze_extracts_keywords(self):
        data = json.dumps({'text': SAMPLE_TEXT, 'title': 'Murakami lives'})
        _, response = app.test_client.post('/analyze', data=data)
        assert response.status == 200
        assert response.json.get('keywords')

    def test_analyze_extracts_summary(self):
        data = json.dumps({'text': SAMPLE_TEXT, 'title': 'Murakami lives'})
        _, response = app.test_client.post('/analyze', data=data)
        assert response.status == 200
        assert response.json.get('summary')

    def test_analyze_lists_all_known_officials_mentioned_in_text(self):
        Official.create(first_name='Grace', last_name='Meng',
                        mv_key='grace-meng')
        Official.create(first_name='Heidi', last_name='Heitkamp',
                        mv_key='heidi-heitkamp')
        text = """
        Once a trump man went to see heidi heitkamp and you what? Grace Meng
        showed up. Whoa Al gRacE meNg was a snopper!
        """
        data = json.dumps({'text': text, 'title': 'Murakami lives'})
        _, response = app.test_client.post('/analyze', data=data)
        expected_ids = compile_official_ids(['Heitkamp', 'Meng'])
        assert response.status == 200

        officials = response.json.get('mentioned_officials')
        ids = sorted(o['official_id'] for o in officials)
        counts = [o['mentioned_count'] for o in officials]
        assert ids == expected_ids
        assert counts == [1, 2]
        Official.delete().execute()


def compile_official_ids(last_names):
    officials = Official.select().where(Official.last_name << last_names)
    return sorted(str(official.id) for official in officials)

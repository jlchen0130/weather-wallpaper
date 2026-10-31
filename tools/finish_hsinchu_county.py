from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json

ROOT = Path(r'D:\projects\weather_wallpaper\pic\knitted\person')
DOWNLOADS = Path(r'C:\Users\JL\Downloads')
PERIODS = ['morning', 'afternoon', 'sunset', 'night', 'midnight', 'sunrise']


def accept(source, period, weather='partly_cloudy'):
    destination = ROOT / f'none_HsinchuCounty_person_{period}_{weather}.png'
    assert not destination.exists(), destination
    with Image.open(source) as image:
        assert image.format == 'JPEG' and image.size == (1536, 2752)
        temporary = destination.with_suffix('.pending')
        assert not temporary.exists()
        image.save(temporary, 'PNG')
    temporary.rename(destination)
    with Image.open(destination) as image:
        assert image.format == 'PNG' and image.size == (1536, 2752)
    print(destination.name)


def build_sheets():
    for weather in ['sunny', 'partly_cloudy']:
        sheet = Image.new('RGB', (1620, 2100), '#171717')
        draw = ImageDraw.Draw(sheet)
        for index, period in enumerate(PERIODS):
            filename = f'none_HsinchuCounty_person_{period}_{weather}.png'
            with Image.open(ROOT / filename) as image:
                assert image.format == 'PNG' and image.size == (1536, 2752)
                thumb = image.resize((512, 918), Image.Resampling.LANCZOS)
            x = 24 + index % 3 * 530
            y = 24 + index // 3 * 1026
            sheet.paste(thumb, (x, y))
            draw.text((x + 8, y + 926), period, font=ImageFont.load_default(size=24), fill='white')
            label = f'none_HsinchuCounty_person_\n{period}_{weather}.png'
            draw.multiline_text((x + 8, y + 958), label, font=ImageFont.load_default(size=17), fill='white', spacing=3)
        sheet.save(ROOT / f'qa/HsinchuCounty_{weather}_6grid.png', 'PNG')


def qualify():
    path = ROOT / 'qa/qualified_assets.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    original_other = {key: [e for e in value if e.get('city') != 'HsinchuCounty'] for key, value in data.items()}
    for weather in ['sunny', 'partly_cloudy']:
        if not any(e.get('city') == 'HsinchuCounty' and e.get('weather') == weather for e in data['qualified_groups']):
            data['qualified_groups'].append(dict(city='HsinchuCounty', style='knitted', character='person', weather=weather, periods=PERIODS, qa_file=f'HsinchuCounty_{weather}_6grid.png', qualified_at='2026-10-09', criteria='Six-period visual QA passed; original Gemini JPEGs and final PNGs verified 1536x2752; daytime sun, sunset setting sun, night and midnight moon, sunrise rising sun; HsinchuCounty rural foothills and tea fields; fine matte needle-felt; no text, watermark or phone UI.'))
    weather_types = ['cloudy', 'overcast', 'light_rain', 'heavy_rain', 'typhoon', 'fog', 'haze', 'strong_wind', 'thunder_shower', 'thunderstorm', 'heatwave', 'cold_wave']
    for weather in weather_types:
        if not any(e.get('city') == 'HsinchuCounty' and e.get('weather') == weather for e in data['qualified_all_day']):
            criteria = 'Existing all-day visual QA reused; original Gemini download and final PNG verified 1536x2752; weather visible, fine matte needle-felt, no large text, watermark or phone UI.'
            if weather in ['heavy_rain', 'typhoon']:
                criteria += ' Sealed indoor composition behind closed glass; exterior roads, paths and foreground empty of people, animals, bicycles, vehicles and vendors.'
            data['qualified_all_day'].append(dict(city='HsinchuCounty', style='knitted', character='person', weather=weather, asset_file=f'none_HsinchuCounty_person_all_day_{weather}.png', master_file='master/none_HsinchuCounty_person_master.png', qa_file='HsinchuCounty_all_day_12grid.png', qualified_at='2026-10-09', criteria=criteria))
    assert original_other == {key: [e for e in value if e.get('city') != 'HsinchuCounty'] for key, value in data.items()}
    temporary = path.with_suffix('.pending')
    assert not temporary.exists()
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)
    print('Qualified 2 regular groups and 12 all-day assets')


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == 'sheets':
        build_sheets()
    elif len(sys.argv) == 2 and sys.argv[1] == 'qualify':
        qualify()
    elif len(sys.argv) == 3 and sys.argv[1] == 'baseline':
        caches = list(Path(r'C:\Users\JL\AppData\Roaming\Codex').rglob('Cache_Data'))
        paths = list(DOWNLOADS.glob('*')) + [p for cache in caches for p in cache.glob('f_*')]
        state = {str(p): [p.stat().st_size, p.stat().st_mtime_ns] for p in paths if p.is_file()}
        Path(sys.argv[2]).write_text(json.dumps(state), encoding='utf-8')
        print('Download and cache baseline recorded')
    elif len(sys.argv) == 3:
        accept(Path(sys.argv[1]), sys.argv[2])
    else:
        with Image.open(ROOT / 'master/none_HsinchuCounty_person_master.png') as image:
            assert image.format == 'PNG' and image.size == (1536, 2752)
        baseline = (DOWNLOADS / 'd9422de1-ba56-45ec-96fb-209acfc06035.tmp').stat().st_mtime
        sources = sorted((p for p in DOWNLOADS.glob('*.tmp') if p.stat().st_mtime > baseline), key=lambda p: p.stat().st_mtime)
        assert len(sources) == 9, len(sources)
        jobs = [(w, p) for w in ['sunny', 'partly_cloudy'] for p in PERIODS][:9]
        for source, (weather, period) in zip(sources, jobs):
            accept(source, period, weather)

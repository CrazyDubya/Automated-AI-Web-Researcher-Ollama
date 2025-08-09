import yaml, pathlib, dataclasses
from typing import List, Dict, Any

@dataclasses.dataclass
class RadarConfig:
    raw: Dict[str, Any]
    timezone: str
    storage_base: pathlib.Path
    reports_dir: pathlib.Path
    ethics: Dict[str, Any]
    llm: Dict[str, Any]
    outputs: Dict[str, Any]
    watchlist: Dict[str, Any]
    topics: List[Dict[str, Any]]

    @property
    def base_dir(self) -> pathlib.Path:
        return self.storage_base


def load(path: pathlib.Path) -> RadarConfig:
    data = yaml.safe_load(path.read_text())
    base_dir = pathlib.Path(data['storage']['base_dir']).expanduser().resolve()
    reports_dir = pathlib.Path(data['storage']['reports_dir']).expanduser().resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / 'daily').mkdir(parents=True, exist_ok=True)
    (reports_dir / 'weekly').mkdir(parents=True, exist_ok=True)
    (reports_dir / 'dossiers').mkdir(parents=True, exist_ok=True)
    return RadarConfig(
        raw=data,
        timezone=data.get('timezone', 'UTC'),
        storage_base=base_dir,
        reports_dir=reports_dir,
        ethics=data.get('ethics', {}),
        llm=data.get('llm', {}),
        outputs=data.get('outputs', {}),
        watchlist=data.get('watchlist', {}),
        topics=data.get('topics', []),
    )
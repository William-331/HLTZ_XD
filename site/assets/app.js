(() => {
  'use strict';
  const data = window.KOUZI_PROFILE;
  const $ = id => document.getElementById(id);
  if (!data || data.schema_version !== 1) {
    $('reply').textContent = '成长记录暂时没有读到，请稍后再来看扣子。';
    $('sync-info').textContent = '数据文件缺失，未使用虚构经验代替。';
    return;
  }
  const pet = data.pet;
  const storageKey = `kouzi.home.${data.username}`;
  const systemTheme = matchMedia('(prefers-color-scheme: dark)');
  let theme = 'system';
  let action = pet.action;
  const validActions = ['idle', 'feed', 'play', 'sleep'];
  function loadLocal() {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
      if (saved && ['light', 'dark', 'system'].includes(saved.theme)) theme = saved.theme;
      if (saved && validActions.includes(saved.action) && Number.isFinite(saved.at) && Date.now() - saved.at >= 0 && Date.now() - saved.at < 86400000) action = saved.action;
    } catch (_) { /* A blocked browser store does not block the cat home. */ }
  }
  function saveLocal() {
    try { localStorage.setItem(storageKey, JSON.stringify({ theme, action, at: Date.now() })); } catch (_) { /* Local storage is optional. */ }
  }
  function currentTheme() { return theme === 'system' ? (systemTheme.matches ? 'dark' : 'light') : theme; }
  function renderRoom() {
    const appearance = currentTheme();
    document.documentElement.dataset.theme = appearance;
    $('theme-toggle').textContent = appearance === 'dark' ? '☀' : '☾';
    $('theme-toggle').setAttribute('aria-label', appearance === 'dark' ? '切换为浅色猫窝' : '切换为深色猫窝');
    $('room-art').src = `assets/kouzi-${action}-${appearance}.svg`;
    const moods = { idle: pet.status, feed: '吃饱了，心情很好', play: '和毛线球搏斗中', sleep: '今天也要好好休息' };
    $('room-art').alt = `${pet.name}的像素猫窝：${moods[action]}`;
    $('mood').textContent = `今日状态 · ${moods[action]}`;
    document.querySelectorAll('[data-action]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.action === action)));
  }
  function interact(next, save = true) {
    if (!validActions.includes(next)) return;
    action = next;
    const messages = { idle: '今天的进度，从一声喵开始。', feed: '咔嚓咔嚓。扣子宣布：你现在是它最喜欢的人。', play: '毛线球逃跑失败，扣子胜利！它还想再玩一会。', sleep: '已进入省电模式。休息不扣经验，晚安。' };
    $('reply').textContent = messages[action];
    renderRoom();
    if (save) saveLocal();
  }
  function span(className, text) {
    const element = document.createElement('span');
    element.className = className;
    element.textContent = text;
    return element;
  }
  loadLocal();
  $('level').textContent = `Lv. ${pet.level} · ${pet.title}`;
  $('xp-value').textContent = `${pet.xp_in_level} / 60 XP`;
  $('xp-fill').style.width = `${Math.min(100, Math.max(0, pet.xp_in_level / 60 * 100))}%`;
  $('xp-progress').setAttribute('aria-valuenow', String(pet.xp_in_level));
  $('xp-note').textContent = `再攒 ${pet.xp_to_next} XP，就能迎来下一次成长。`;
  $('growth-copy').textContent = `从 ${pet.adopted_on} 开始一起生活，已经积攒 ${pet.total_xp} XP。`;
  $('unlocks').textContent = pet.unlocks.join(' · ');
  $('sync-info').textContent = `${data.source === 'github' ? '已连接 GitHub' : '演示数据，尚未连接 GitHub'} · 同步于 ${data.updated_on} · 今日 ${data.today.contributions} 次贡献 / ${data.today.earned_xp} XP · 每日更新，可能有延迟。`;
  const icons = { Python: '⌘', JavaScript: '✦', TypeScript: '◇', HTML: '▧', Jupyter: '⌘', 'Jupyter Notebook': '⌘', Rust: '⚙', Go: '◇' };
  for (const repo of data.projects) {
    // Never insert repository descriptions or names as HTML.
    const url = new URL(repo.url);
    if (url.protocol !== 'https:' || url.hostname !== 'github.com') continue;
    const link = document.createElement('a');
    link.className = 'project';
    link.href = url.href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    const icon = span('project-icon', icons[repo.language] || '✧');
    icon.setAttribute('aria-hidden', 'true');
    const text = document.createElement('span');
    text.append(span('project-name', repo.name), span('project-description', repo.description), span('project-meta', `${repo.language} · ${repo.updated_on} 更新${repo.featured ? ' · 常驻项目' : ''}`));
    const arrow = span('project-arrow', '↗');
    arrow.setAttribute('aria-hidden', 'true');
    link.append(icon, text, arrow);
    $('projects').append(link);
  }
  if (!data.projects.length) $('projects').textContent = '扣子正在等第一个有内容的公开项目。';
  for (const day of data.week) {
    const item = document.createElement('li');
    item.dataset.count = String(day.count);
    item.setAttribute('aria-label', `${day.date}：${day.count} 次贡献`);
    const mark = span('footprint-mark', day.count ? '🐾' : '☾');
    mark.setAttribute('aria-hidden', 'true');
    item.append(mark, span('footprint-date', day.date.slice(5)), span('footprint-count', `${day.count} 次`));
    $('footprints').append(item);
  }
  const stage = pet.level >= 6 ? 3 : pet.level >= 4 ? 2 : pet.level >= 2 ? 1 : 0;
  document.querySelectorAll('[data-stage]').forEach(element => {
    const active = Number(element.dataset.stage) === stage;
    element.classList.toggle('is-current', active);
    if (active) element.setAttribute('aria-current', 'step');
  });
  document.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => interact(button.dataset.action)));
  $('theme-toggle').addEventListener('click', () => { theme = currentTheme() === 'dark' ? 'light' : 'dark'; saveLocal(); renderRoom(); });
  systemTheme.addEventListener('change', () => { if (theme === 'system') renderRoom(); });
  const deepAction = new URLSearchParams(location.search).get('action');
  interact(validActions.includes(deepAction) ? deepAction : action, Boolean(deepAction));
})();

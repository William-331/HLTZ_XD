(() => {
  'use strict';
  const data = window.KOUZI_PROFILE;
  const $ = id => document.getElementById(id);
  if (!data || ![1, 2].includes(data.schema_version)) {
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
  const repositories = data.repositories || data.projects;
  const recentNames = new Set(data.projects.map(repo => repo.name));
  let libraryMode = 'featured';
  let openedProject = null;
  $('repo-count').textContent = `${repositories.length} 本公开项目笔记`;
  function safeSource(value) {
    try { const url = new URL(value); return url.protocol === 'https:' && url.hostname === 'github.com' ? url.href : null; } catch (_) { return null; }
  }
  // A small, offline text renderer: no repository HTML, scripts, embeds or remote images.
  function renderNotes(markdown, container) {
    container.replaceChildren();
    if (!markdown) { container.textContent = '这本笔记还没有 README。项目资料会随仓库更新自动同步。'; return; }
    let code = null;
    for (const line of markdown.split(/\r?\n/)) {
      if (/^\s*```/.test(line)) { if (code) { code = null; } else { code = document.createElement('pre'); container.append(code); } continue; }
      if (code) { code.textContent += line + '\n'; continue; }
      const text = line.replace(/<!--.*?-->/g, '').replace(/<[^>]*>/g, '').replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1').replace(/\*\*([^*]+)\*\*/g, '$1').replace(/`([^`]+)`/g, '$1').trim();
      if (!text || /^[-_*]{3,}$/.test(text)) continue;
      const node = document.createElement(/^#{1,6}\s/.test(text) ? 'h5' : 'p');
      node.textContent = text.replace(/^#{1,6}\s+/, '').replace(/^[-*+]\s+/, '• ');
      container.append(node);
    }
  }
  function openProject(repo, focus = true) {
    openedProject = repo.name;
    $('repo-detail').hidden = false;
    $('detail-title').textContent = repo.name;
    $('detail-description').textContent = repo.description;
    $('detail-meta').textContent = `${repo.language} · ${repo.updated_on} 更新 · ☆ ${repo.stars || 0} · ${repo.forks || 0} forks${repo.archived ? ' · 已归档' : ''}${repo.fork ? ' · fork 项目' : ''}`;
    $('detail-topics').replaceChildren(...(repo.topics || []).map(topic => span('topic', topic)));
    renderNotes(repo.readme, $('detail-readme'));
    if (repo.readme_truncated) $('detail-readme').append(span('section-note', '笔记较长，这里展示前 24,000 个字符；完整内容可从源码入口查看。'));
    const source = safeSource(repo.url);
    $('detail-source').hidden = !source;
    if (source) $('detail-source').href = source;
    document.querySelectorAll('[data-repo-name]').forEach(button => button.setAttribute('aria-expanded', String(button.dataset.repoName === repo.name)));
    if (focus) { $('detail-title').focus({ preventScroll: true }); $('repo-detail').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'nearest' }); }
  }
  function renderLibrary() {
    const term = $('repo-search').value.toLowerCase().trim();
    const results = repositories.filter(repo => (libraryMode === 'all' || recentNames.has(repo.name)) && `${repo.name} ${repo.description} ${repo.language} ${(repo.topics || []).join(' ')}`.toLowerCase().includes(term));
    $('projects').replaceChildren();
    for (const repo of results) {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'project'; button.dataset.repoName = repo.name;
      button.setAttribute('aria-expanded', String(openedProject === repo.name));
      button.setAttribute('aria-controls', 'repo-detail');
      const icon = span('project-icon', icons[repo.language] || '✧'); icon.setAttribute('aria-hidden', 'true');
      const text = document.createElement('span');
      text.append(span('project-name', repo.name), span('project-description', repo.description), span('project-meta', `${repo.language} · ${repo.updated_on} 更新${repo.featured ? ' · 常驻项目' : ''}`));
      const arrow = span('project-arrow', '+'); arrow.setAttribute('aria-hidden', 'true');
      button.append(icon, text, arrow); button.addEventListener('click', () => openProject(repo)); $('projects').append(button);
    }
    if (!results.length) $('projects').textContent = term ? '扣子翻遍书架，还没找到这个项目。' : '扣子正在等第一本项目笔记。';
    $('library-note').textContent = `${results.length} 个项目 · 点开查看详情和 README，不用离开猫窝。`;
  }
  $('detail-title').setAttribute('tabindex', '-1');
  document.querySelectorAll('[data-library]').forEach(button => button.addEventListener('click', () => {
    libraryMode = button.dataset.library;
    document.querySelectorAll('[data-library]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    renderLibrary();
  }));
  $('repo-search').addEventListener('input', renderLibrary);
  $('close-detail').addEventListener('click', () => {
    const oldName = openedProject; openedProject = null; $('repo-detail').hidden = true;
    document.querySelectorAll('[data-repo-name]').forEach(button => { button.setAttribute('aria-expanded', 'false'); if (button.dataset.repoName === oldName) button.focus({ preventScroll: true }); });
  });
  renderLibrary();
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
  const year = data.calendar;
  let calendarMode = 'year';
  let selectedDate = data.today.date;
  function intensity(count) { return count === 0 ? 0 : count <= 3 ? 1 : count <= 9 ? 2 : count <= 15 ? 3 : 4; }
  function renderCalendar() {
    const days = year ? (calendarMode === 'year' ? year.days : year.days.slice(-90)) : data.week;
    const grid = $('calendar-grid'); grid.replaceChildren();
    grid.dataset.range = calendarMode;
    const start = new Date(days[0].date + 'T00:00:00Z');
    const offset = start.getUTCDay();
    const columns = Math.ceil((offset + days.length) / 7);
    grid.style.setProperty('--weeks', String(columns));
    const byDate = new Map(days.map(day => [day.date, day]));
    const total = year && calendarMode === 'year' ? year.total : days.reduce((sum, day) => sum + day.count, 0);
    $('calendar-total').textContent = `${total} 次贡献 · ${days[0].date} — ${days[days.length - 1].date}${calendarMode === 'year' && year ? ` · ${year.active_days} 个有足迹的日子` : ''}`;
    let previousMonth = -1;
    for (let column = 0; column < columns; column++) {
      const d = new Date(start.getTime() + (column * 7 - offset) * 86400000);
      const label = span('calendar-month', '');
      const month = d.getUTCMonth();
      if (month !== previousMonth) { label.textContent = `${month + 1}月`; previousMonth = month; }
      label.style.gridColumn = String(column + 1); label.style.gridRow = '1'; grid.append(label);
    }
    for (let index = 0; index < columns * 7; index++) {
      const d = new Date(start.getTime() + (index - offset) * 86400000);
      const key = d.toISOString().slice(0, 10); const day = byDate.get(key);
      const cell = document.createElement(day ? 'button' : 'span');
      cell.className = 'calendar-day'; cell.style.gridColumn = String(Math.floor(index / 7) + 1); cell.style.gridRow = String(index % 7 + 2);
      if (day) {
        cell.type = 'button'; cell.dataset.intensity = String(intensity(day.count)); cell.dataset.date = key;
        cell.title = `${key} · ${day.count} 次贡献`;
        cell.setAttribute('aria-label', `${key}，${day.count} 次贡献`);
        cell.setAttribute('aria-pressed', String(key === selectedDate));
        cell.tabIndex = key === selectedDate ? 0 : -1;
        cell.addEventListener('click', () => selectDay(day));
        cell.addEventListener('keydown', event => {
          const deltas = { ArrowLeft: -7, ArrowRight: 7, ArrowUp: -1, ArrowDown: 1 };
          let target;
          if (Object.hasOwn(deltas, event.key)) target = new Date(d.getTime() + deltas[event.key] * 86400000).toISOString().slice(0, 10);
          else if (event.key === 'Home') target = days[0].date;
          else if (event.key === 'End') target = days[days.length - 1].date;
          else return;
          event.preventDefault();
          if (byDate.has(target)) { selectDay(byDate.get(target)); grid.querySelector(`[data-date="${target}"]`).focus(); }
        });
      } else { cell.classList.add('is-empty'); cell.setAttribute('aria-hidden', 'true'); }
      grid.append(cell);
    }
    if (!byDate.has(selectedDate)) selectedDate = days[days.length - 1].date;
    selectDay(byDate.get(selectedDate));
  }
  function selectDay(day) {
    selectedDate = day.date;
    const earned = day.date >= pet.adopted_on ? (day.count === 0 ? 0 : day.count <= 3 ? 5 : day.count <= 9 ? 8 : 10) : null;
    $('calendar-selected').textContent = `${day.date} · ${day.count ? `🐾 ${day.count} 次贡献` : '☾ 休息的一天'}${earned === null ? ' · 领养前的足迹' : ` · 当日贡献对应 ${earned} XP`}`;
    document.querySelectorAll('.calendar-day[data-date]').forEach(button => { const selected = button.dataset.date === selectedDate; button.setAttribute('aria-pressed', String(selected)); button.tabIndex = selected ? 0 : -1; });
  }
  document.querySelectorAll('[data-calendar]').forEach(button => button.addEventListener('click', () => {
    calendarMode = button.dataset.calendar;
    document.querySelectorAll('[data-calendar]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    renderCalendar();
  }));
  renderCalendar();
  const activity = data.activity || [];
  let activityLimit = 8;
  function renderActivity() {
    $('activity-list').replaceChildren();
    let month = '';
    for (const entry of activity.slice(0, activityLimit)) {
      if (entry.date.slice(0, 7) !== month) {
        month = entry.date.slice(0, 7); const heading = document.createElement('h4');
        heading.className = 'journal-month'; heading.textContent = `${month.slice(0, 4)} 年 ${Number(month.slice(5))} 月`; $('activity-list').append(heading);
      }
      const row = document.createElement('article'); row.className = 'journal-entry';
      const stamp = span('journal-stamp', entry.kind === 'commit' ? '⌘' : entry.kind === 'create' ? '✦' : '◇'); stamp.setAttribute('aria-hidden', 'true');
      const info = document.createElement('div'); const description = document.createElement('p'); description.textContent = entry.title;
      const name = entry.repo.split('/').slice(1).join('/'); const repository = repositories.find(r => r.name === name && entry.repo.split('/')[0].toLowerCase() === data.username.toLowerCase());
      const label = document.createElement(repository ? 'button' : 'span'); label.className = 'journal-repo'; label.textContent = entry.repo;
      if (repository) { label.type = 'button'; label.addEventListener('click', () => { libraryMode = 'all'; $('repo-search').value = ''; document.querySelectorAll('[data-library]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.library === 'all'))); renderLibrary(); openProject(repository); }); }
      info.append(description, label); const dateLabel = document.createElement('time'); dateLabel.dateTime = entry.date; dateLabel.textContent = entry.date.slice(5);
      row.append(stamp, info, dateLabel); $('activity-list').append(row);
    }
    if (!activity.length) $('activity-list').textContent = '最近还没有公开的代码日记。扣子会等你的下一个故事。';
    $('more-activity').hidden = activityLimit >= activity.length;
  }
  $('more-activity').addEventListener('click', () => { activityLimit += 8; renderActivity(); });
  renderActivity();
  const organizations = data.organizations || [];
  if (organizations.length) {
    $('organizations').hidden = false;
    for (const organization of organizations) {
      const group = document.createElement('div'); group.className = 'organization';
      group.append(span('organization-name', organization.login), span('organization-copy', organization.description || '公开加入的组织'));
      $('organization-list').append(group);
    }
  }
  $('visibility-note').textContent = data.visibility_note || '只展示公开信息；登录后的 GitHub 活动视图可能不同。';
  document.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => interact(button.dataset.action)));
  $('theme-toggle').addEventListener('click', () => { theme = currentTheme() === 'dark' ? 'light' : 'dark'; saveLocal(); renderRoom(); });
  systemTheme.addEventListener('change', () => { if (theme === 'system') renderRoom(); });
  const deepAction = new URLSearchParams(location.search).get('action');
  interact(validActions.includes(deepAction) ? deepAction : action, Boolean(deepAction));
})();

/**
 * EventBus — Modüller arası kurye
 * emit(event, data) → tüm listener'ları tetikler
 * on(event, handler) → listener ekle
 * off(event, handler) → listener kaldır
 * once(event, handler) → tek seferlik listener
 */
const EventBus = (() => {
  const _handlers = {};

  function on(event, handler) {
    if (!_handlers[event]) _handlers[event] = [];
    _handlers[event].push(handler);
  }

  function off(event, handler) {
    if (_handlers[event]) {
      _handlers[event] = _handlers[event].filter(h => h !== handler);
    }
  }

  function emit(event, data) {
    (_handlers[event] || []).slice().forEach(h => {
      try { h(data); }
      catch(e) { console.error(`[EventBus] ${event} handler error:`, e); }
    });
  }

  function once(event, handler) {
    function wrapper(data) {
      handler(data);
      off(event, wrapper);
    }
    on(event, wrapper);
  }

  function debug() {
    console.table(Object.keys(_handlers).map(e => ({
      event: e, listeners: _handlers[e].length
    })));
  }

  return { on, off, emit, once, debug };
})();

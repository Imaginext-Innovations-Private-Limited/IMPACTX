const tileSize = 256;

// The overview extends beyond the city core to include Devanahalli and Electronic City.
export const bengaluruExtent = [
  { latitude: 13.269, longitude: 77.435 },
  { latitude: 12.810, longitude: 77.800 },
];

export function project(latitude, longitude, zoom) {
  const radians = latitude * Math.PI / 180;
  const size = tileSize * 2 ** zoom;
  return {
    x: (longitude + 180) / 360 * size,
    y: (1 - Math.asinh(Math.tan(radians)) / Math.PI) / 2 * size,
  };
}

export function unproject(x, y, zoom) {
  const size = tileSize * 2 ** zoom;
  return {
    latitude: Math.atan(Math.sinh(Math.PI * (1 - 2 * y / size))) * 180 / Math.PI,
    longitude: x / size * 360 - 180,
  };
}

function distanceMeters(lat1, lon1, lat2, lon2) {
  const rad = Math.PI / 180;
  const a = Math.sin((lat2 - lat1) * rad / 2) ** 2 +
    Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin((lon2 - lon1) * rad / 2) ** 2;
  return 12742000 * Math.asin(Math.sqrt(Math.min(1, a)));
}

export function nearestZone(lake, { latitude, longitude, accuracy }) {
  if (!lake.center || ![latitude, longitude, accuracy].every(Number.isFinite) ||
      Math.abs(latitude) > 90 || Math.abs(longitude) > 180 || accuracy < 0 || accuracy > 150 ||
      distanceMeters(latitude, longitude, ...lake.center) > lake.gpsRadius) return null;
  let nearest = null;
  let best = Infinity;
  for (const zone of lake.zones) {
    const distance = distanceMeters(latitude, longitude, zone.latitude, zone.longitude);
    if (distance < best) {
      nearest = zone;
      best = distance;
    }
  }
  return nearest;
}

export function fitMap(points, width, height, maxZoom, padding = 44) {
  const positions = points.map(({ latitude, longitude }) => project(latitude, longitude, 0));
  const xs = positions.map(point => point.x);
  const ys = positions.map(point => point.y);
  const west = Math.min(...xs), east = Math.max(...xs);
  const north = Math.min(...ys), south = Math.max(...ys);
  const fraction = Math.min(
    Math.max(1, width - padding * 2) / (east - west),
    Math.max(1, height - padding * 2) / (south - north),
  );
  const zoom = Math.max(0, Math.min(maxZoom, Math.floor(Math.log2(fraction))));
  const scale = 2 ** zoom;
  return {
    zoom, width, height,
    left: Math.round((west + east) / 2 * scale - width / 2),
    top: Math.round((north + south) / 2 * scale - height / 2),
  };
}

function drawTiles(layer, { left, top, zoom, width, height }) {
  const firstX = Math.floor(left / tileSize);
  const firstY = Math.floor(top / tileSize);
  const lastX = Math.floor((left + width - 1) / tileSize);
  const lastY = Math.floor((top + height - 1) / tileSize);

  const reusable = new Map([...layer.children].map(tile => [tile.dataset.tile, tile]));
  const visible = new Set();
  const world = 2 ** zoom;
  for (let x = firstX; x <= lastX; x++) {
    for (let y = firstY; y <= lastY; y++) {
      if (y < 0 || y >= world) continue;
      const key = zoom + '/' + x + '/' + y;
      visible.add(key);
      let tile = reusable.get(key);
      if (!tile) {
        tile = new Image(tileSize, tileSize);
        tile.alt = '';
        tile.dataset.tile = key;
        tile.draggable = false;
        tile.src = 'https://tile.openstreetmap.org/' + zoom + '/' + ((x % world + world) % world) + '/' + y + '.png';
        layer.append(tile);
      }
      tile.style.left = (x * tileSize - left) + 'px';
      tile.style.top = (y * tileSize - top) + 'px';
    }
  }
  for (const [key, tile] of reusable) if (!visible.has(key)) tile.remove();
}

export function drawMap(container, layer, points, markers, maxZoom, padding) {
  const { width, height } = container.getBoundingClientRect();
  if (!width || !height || !points.length) return null;
  const viewport = fitMap(points, width, height, maxZoom, padding);
  renderViewport(layer, points, markers, viewport);
  return viewport;
}

export function renderViewport(layer, points, markers, viewport) {
  if (layer) drawTiles(layer, viewport);
  placeMarkers(points, markers, viewport);
}

export function placeMarkers(points, markers, viewport) {
  const indexed = new Map(points.map(point => [point.id, point]));
  for (const marker of markers.children) {
    const point = indexed.get(marker.dataset.mapId);
    if (!point) continue;
    const location = project(point.latitude, point.longitude, viewport.zoom);
    const x = location.x - viewport.left;
    const y = location.y - viewport.top;
    marker.style.left = x + 'px';
    marker.style.top = y + 'px';
    marker.toggleAttribute('data-offscreen', x < 12 || y < 20 || x > viewport.width - 12 || y > viewport.height - 12);
  }
}

export function zoomViewport(viewport, zoom, x, y, nextX = x, nextY = y) {
  const scale = 2 ** (zoom - viewport.zoom);
  return {
    ...viewport, zoom,
    left: (viewport.left + x) * scale - nextX,
    top: (viewport.top + y) * scale - nextY,
  };
}

export function interactiveMap(surface, render, pick, captureScroll = () => true) {
  const pointers = new Map();
  let viewport;
  let fitted = true;
  let fitTarget;
  let dragged = false;
  let frame;
  let wheelTime = -Infinity;
  const minZoom = 9;
  const maxZoom = 19;
  const clampZoom = zoom => Math.min(maxZoom, Math.max(minZoom, zoom));
  function draw() {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = undefined;
      if (viewport) render(viewport);
    });
  }
  function fit(points = bengaluruExtent, shoreline = false) {
    const { clientWidth: width, clientHeight: height } = surface;
    viewport = fitMap(points, width, height, shoreline ? 18 : 13, shoreline ? 44 : 32);
    fitTarget = [points, shoreline];
    fitted = true;
    draw();
  }
  function zoomBy(amount, x = viewport.width / 2, y = viewport.height / 2) {
    const zoom = clampZoom(viewport.zoom + amount);
    if (zoom === viewport.zoom) return;
    viewport = zoomViewport(viewport, zoom, x, y);
    fitted = false;
    draw();
  }
  function pan(dx, dy) {
    viewport.left -= dx;
    viewport.top -= dy;
    fitted = false;
    draw();
  }
  function relative(x, y) {
    const rect = surface.getBoundingClientRect();
    return { x: x - rect.left, y: y - rect.top };
  }
  function gesture() {
    const [a, b] = pointers.values();
    return b ? {
      x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, span: Math.hypot(a.x - b.x, a.y - b.y),
    } : a;
  }
  let pinchSpan;
  surface.addEventListener('pointerdown', event => {
    if (event.button !== 0 || event.target.closest('button, a')) return;
    if (pointers.size === 0) dragged = false;
    pointers.set(event.pointerId, relative(event.clientX, event.clientY));
    if (pointers.size === 2) {
      dragged = true;
      pinchSpan = gesture().span;
    }
    surface.setPointerCapture(event.pointerId);
  });
  surface.addEventListener('pointermove', event => {
    if (!pointers.has(event.pointerId)) return;
    const before = gesture();
    const point = relative(event.clientX, event.clientY);
    if (!dragged && Math.hypot(point.x - before.x, point.y - before.y) < 5) return;
    pointers.set(event.pointerId, point);
    const after = gesture();
    dragged = true;
    surface.classList.add('is-dragging');
    if (pointers.size > 1 && pinchSpan > 0 && after.span > 0) {
      const steps = Math.log2(after.span / pinchSpan);
      if (Math.abs(steps) >= .65) {
        const zoom = clampZoom(viewport.zoom + Math.sign(steps));
        viewport = zoomViewport(viewport, zoom, before.x, before.y, after.x, after.y);
        pinchSpan = after.span;
        fitted = false;
        draw();
        return;
      }
    }
    pan(after.x - before.x, after.y - before.y);
  });
  for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) {
    surface.addEventListener(type, event => {
      if (!pointers.delete(event.pointerId)) return;
      if (!pointers.size) {
        surface.classList.remove('is-dragging');
        if (type === 'pointerup' && !dragged) {
          const point = relative(event.clientX, event.clientY);
          pick(viewport, point.x, point.y);
        }
      }
    });
  }
  surface.addEventListener('wheel', event => {
    if (!captureScroll()) return;
    event.preventDefault();
    if (performance.now() - wheelTime < 115 || !event.deltaY) return;
    wheelTime = performance.now();
    const point = relative(event.clientX, event.clientY);
    zoomBy(event.deltaY < 0 ? 1 : -1, point.x, point.y);
  }, { passive: false });
  surface.addEventListener('dblclick', event => {
    if (!event.target.closest('button, a')) {
      const point = relative(event.clientX, event.clientY);
      zoomBy(1, point.x, point.y);
    }
  });
  surface.addEventListener('keydown', event => {
    if (event.target !== surface) return;
    const movements = { ArrowUp: [0, 90], ArrowDown: [0, -90], ArrowLeft: [90, 0], ArrowRight: [-90, 0] };
    if (movements[event.key]) pan(...movements[event.key]);
    else if (event.key === '+' || event.key === '=') zoomBy(1);
    else if (event.key === '-') zoomBy(-1);
    else if (event.key === 'Home') fit(...fitTarget);
    else return;
    event.preventDefault();
  });
  fit();
  new ResizeObserver(() => {
    if (fitted) fit(...fitTarget);
    else {
      const { clientWidth: width, clientHeight: height } = surface;
      viewport.left += (viewport.width - width) / 2;
      viewport.top += (viewport.height - height) / 2;
      Object.assign(viewport, { width, height });
      draw();
    }
  }).observe(surface);
  return { fit, zoomBy, redraw: draw };
}

export function sectorAt(lake, viewport, x, y) {
  if (!viewport) return null;
  const position = unproject(viewport.left + x, viewport.top + y, viewport.zoom);
  const zone = nearestZone(lake, { ...position, accuracy: 0 });
  if (!zone || distanceMeters(position.latitude, position.longitude, zone.latitude, zone.longitude) >
    (lake.shorePickRadius ?? 240)) return null;
  return zone;
}

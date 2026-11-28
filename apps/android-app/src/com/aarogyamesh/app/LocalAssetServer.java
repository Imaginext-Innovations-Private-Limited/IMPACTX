package com.aarogyamesh.app;

import android.content.res.AssetManager;
import android.util.Log;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Lightweight pure-Java loopback HTTP/1.1 asset server bound strictly to 127.0.0.1.
 *
 * Serving bundled PWA assets over http://127.0.0.1:<port> gives Android WebView a
 * genuine W3C Secure Context so IndexedDB, crypto.randomUUID(), Service Workers,
 * and offline getUserMedia() microphone recording work natively without internet.
 */
public final class LocalAssetServer {
    private static final String TAG = "LocalAssetServer";

    /**
     * Preferred port inside the IANA ephemeral range (49152-65535) so the WebView
     * origin stays stable across normal app restarts (preserving IndexedDB & localStorage).
     * Automatically falls back to OS-assigned ephemeral port 0 if busy.
     */
    private static final int PREFERRED_PORT_START = 49842;
    private static final int PREFERRED_PORT_COUNT = 10;
    private static final int SOCKET_TIMEOUT_MS = 10_000;

    /** Suggested LAN PHC Hub address shown as a placeholder in the native Hub URL dialog. */
    public static final String DEFAULT_HUB_URL = "http://192.168.1.14:8000";

    private final AssetManager assets;
    private ServerSocket serverSocket;
    private ExecutorService pool;
    private Thread acceptThread;
    private volatile boolean running;
    private int boundPort = -1;

    public LocalAssetServer(AssetManager assets) {
        this.assets = assets;
    }

    public synchronized int start() throws IOException {
        if (running && boundPort > 0) {
            return boundPort;
        }
        InetAddress loopback = InetAddress.getByName("127.0.0.1");
        ServerSocket ss = null;
        for (int offset = 0; offset < PREFERRED_PORT_COUNT; offset++) {
            int candidatePort = PREFERRED_PORT_START + offset;
            ServerSocket attempt = new ServerSocket();
            attempt.setReuseAddress(true);
            try {
                attempt.bind(new InetSocketAddress(loopback, candidatePort), 64);
                ss = attempt;
                break;
            } catch (IOException busy) {
                try {
                    attempt.close();
                } catch (IOException ignored) {
                }
            }
        }
        if (ss == null) {
            Log.w(TAG, "Preferred ports " + PREFERRED_PORT_START + "-" + (PREFERRED_PORT_START + PREFERRED_PORT_COUNT - 1)
                    + " unavailable; falling back to ephemeral port");
            ss = new ServerSocket();
            ss.setReuseAddress(true);
            ss.bind(new InetSocketAddress(loopback, 0), 64);
        }

        this.serverSocket = ss;
        this.boundPort = ss.getLocalPort();
        this.pool = Executors.newCachedThreadPool();
        this.running = true;

        final ServerSocket activeSocket = ss;
        this.acceptThread = new Thread(new Runnable() {
            @Override
            public void run() {
                acceptLoop(activeSocket);
            }
        }, "AarogyaLocalAssetServer");
        this.acceptThread.setDaemon(true);
        this.acceptThread.start();

        Log.i(TAG, "Bound strictly to http://127.0.0.1:" + boundPort);
        return boundPort;
    }

    public int getPort() {
        return boundPort;
    }

    public String getBaseUrl() {
        return "http://127.0.0.1:" + boundPort;
    }

    public synchronized void stop() {
        running = false;
        if (serverSocket != null) {
            try {
                serverSocket.close();
            } catch (IOException ignored) {
            }
            serverSocket = null;
        }
        if (pool != null) {
            pool.shutdownNow();
            pool = null;
        }
        boundPort = -1;
    }

    private void acceptLoop(ServerSocket ss) {
        while (running && !ss.isClosed()) {
            try {
                final Socket client = ss.accept();
                ExecutorService currentPool = this.pool;
                if (currentPool != null && !currentPool.isShutdown()) {
                    currentPool.execute(new Runnable() {
                        @Override
                        public void run() {
                            handleClient(client);
                        }
                    });
                } else {
                    client.close();
                }
            } catch (IOException e) {
                if (running) {
                    Log.w(TAG, "Accept error: " + e.getMessage());
                }
            }
        }
    }

    private void handleClient(Socket socket) {
        try {
            socket.setSoTimeout(SOCKET_TIMEOUT_MS);
            BufferedReader reader = new BufferedReader(
                    new InputStreamReader(new BufferedInputStream(socket.getInputStream()), StandardCharsets.UTF_8));
            OutputStream out = socket.getOutputStream();

            String requestLine = reader.readLine();
            if (requestLine == null || requestLine.trim().isEmpty()) {
                return;
            }
            // Drain HTTP headers until blank line
            String header;
            while ((header = reader.readLine()) != null && !header.isEmpty()) {
                // No request body expected for GET/HEAD/OPTIONS
            }

            String[] parts = requestLine.split(" ");
            if (parts.length < 2) {
                writeTextResponse(out, 400, "Bad Request", "text/plain; charset=utf-8", "Bad Request", false);
                return;
            }
            String method = parts[0].toUpperCase(Locale.US);
            String rawTarget = parts[1];

            if ("OPTIONS".equals(method)) {
                writeOptionsResponse(out);
                return;
            }
            boolean headOnly = "HEAD".equals(method);
            if (!"GET".equals(method) && !headOnly) {
                writeTextResponse(out, 405, "Method Not Allowed", "text/plain; charset=utf-8", "Method Not Allowed", headOnly);
                return;
            }

            String cleanPath = sanitizePath(rawTarget);
            if (cleanPath == null) {
                writeTextResponse(out, 400, "Bad Request", "text/plain; charset=utf-8", "Invalid path", headOnly);
                return;
            }

            // Canonical redirects: native top bar handles ASHA Field <-> Watch switching directly
            if ("/".equals(cleanPath) || "/index.html".equals(cleanPath) || "/phone".equals(cleanPath)) {
                writeRedirect(out, "/phone/");
                return;
            }
            if ("/watch".equals(cleanPath)) {
                writeRedirect(out, "/watch/");
                return;
            }

            // Favicon fallback to avoid 404 noise in console
            if ("/favicon.ico".equals(cleanPath)) {
                serveAsset(out, "phone/icons/icon-192.png", "image/png", headOnly);
                return;
            }

            // Static bundles from APK assets
            if (cleanPath.startsWith("/phone/")) {
                String rel = cleanPath.substring("/phone/".length());
                if (rel.isEmpty()) {
                    rel = "index.html";
                }
                serveAsset(out, "phone/" + rel, mimeTypeFor(rel), headOnly);
                return;
            }

            if (cleanPath.startsWith("/watch/")) {
                String rel = cleanPath.substring("/watch/".length());
                if (rel.isEmpty()) {
                    rel = "index.html";
                }
                serveAsset(out, "watch/" + rel, mimeTypeFor(rel), headOnly);
                return;
            }

            writeTextResponse(out, 404, "Not Found", "text/plain; charset=utf-8", "Not Found: " + cleanPath, headOnly);
        } catch (IOException ignored) {
            // Client disconnected or timed out
        } catch (Exception e) {
            Log.w(TAG, "Unexpected error handling request: " + e.getMessage());
            try {
                writeTextResponse(socket.getOutputStream(), 500, "Internal Server Error",
                        "text/plain; charset=utf-8", "Internal Server Error", false);
            } catch (IOException ignored) {
            }
        } finally {
            try {
                socket.close();
            } catch (IOException ignored) {
            }
        }
    }

    private void serveAsset(OutputStream out, String assetPath, String mimeType, boolean headOnly)
            throws IOException {
        byte[] data = readAssetBytes(assetPath);
        if (data == null) {
            writeTextResponse(out, 404, "Not Found", "text/plain; charset=utf-8", "Asset not found: " + assetPath, headOnly);
            return;
        }
        writeBytesResponse(out, 200, "OK", mimeType, data, headOnly);
    }

    private byte[] readAssetBytes(String assetPath) {
        InputStream in = null;
        try {
            in = assets.open(assetPath);
            ByteArrayOutputStream buffer = new ByteArrayOutputStream(8192);
            byte[] chunk = new byte[8192];
            int n;
            while ((n = in.read(chunk)) != -1) {
                buffer.write(chunk, 0, n);
            }
            return buffer.toByteArray();
        } catch (IOException e) {
            return null;
        } finally {
            if (in != null) {
                try {
                    in.close();
                } catch (IOException ignored) {
                }
            }
        }
    }

    private static String sanitizePath(String rawTarget) {
        if (rawTarget == null || rawTarget.isEmpty()) {
            return "/";
        }
        int q = rawTarget.indexOf('?');
        String path = q >= 0 ? rawTarget.substring(0, q) : rawTarget;
        int hash = path.indexOf('#');
        if (hash >= 0) {
            path = path.substring(0, hash);
        }
        try {
            path = URLDecoder.decode(path, "UTF-8");
        } catch (Exception e) {
            return null;
        }
        if (!path.startsWith("/") || path.contains("..") || path.contains("\\") || path.indexOf('\0') >= 0) {
            return null;
        }
        while (path.contains("//")) {
            path = path.replace("//", "/");
        }
        return path;
    }

    public static String mimeTypeFor(String path) {
        String lower = path.toLowerCase(Locale.US);
        if (lower.endsWith(".html") || lower.endsWith(".htm")) {
            return "text/html; charset=utf-8";
        }
        if (lower.endsWith(".js") || lower.endsWith(".mjs")) {
            return "application/javascript; charset=utf-8";
        }
        if (lower.endsWith(".css")) {
            return "text/css; charset=utf-8";
        }
        if (lower.endsWith(".svg")) {
            return "image/svg+xml";
        }
        if (lower.endsWith(".png")) {
            return "image/png";
        }
        if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) {
            return "image/jpeg";
        }
        if (lower.endsWith(".webp")) {
            return "image/webp";
        }
        if (lower.endsWith(".ico")) {
            return "image/x-icon";
        }
        if (lower.endsWith(".webmanifest")) {
            return "application/manifest+json; charset=utf-8";
        }
        if (lower.endsWith(".json") || lower.endsWith(".map")) {
            return "application/json; charset=utf-8";
        }
        if (lower.endsWith(".wasm")) {
            return "application/wasm";
        }
        return "application/octet-stream";
    }

    private static void writeRedirect(OutputStream out, String location) throws IOException {
        String resp = "HTTP/1.1 302 Found\r\n"
                + "Location: " + location + "\r\n"
                + "Content-Length: 0\r\n"
                + "Cache-Control: no-store\r\n"
                + "Connection: close\r\n\r\n";
        out.write(resp.getBytes(StandardCharsets.US_ASCII));
        out.flush();
    }

    private static void writeOptionsResponse(OutputStream out) throws IOException {
        String resp = "HTTP/1.1 204 No Content\r\n"
                + "Allow: GET, HEAD, OPTIONS\r\n"
                + "Content-Length: 0\r\n"
                + "Cache-Control: no-store\r\n"
                + "Connection: close\r\n\r\n";
        out.write(resp.getBytes(StandardCharsets.US_ASCII));
        out.flush();
    }

    private static void writeTextResponse(OutputStream out, int code, String reason, String contentType, String text, boolean headOnly)
            throws IOException {
        writeBytesResponse(out, code, reason, contentType, text.getBytes(StandardCharsets.UTF_8), headOnly);
    }

    private static void writeBytesResponse(OutputStream out, int code, String reason, String contentType, byte[] body, boolean headOnly)
            throws IOException {
        String cacheControl = code >= 400 ? "no-store" : "no-cache";
        String header = "HTTP/1.1 " + code + " " + reason + "\r\n"
                + "Content-Type: " + contentType + "\r\n"
                + "Content-Length: " + body.length + "\r\n"
                + "Cache-Control: " + cacheControl + "\r\n"
                + "X-Content-Type-Options: nosniff\r\n"
                + "Connection: close\r\n\r\n";
        out.write(header.getBytes(StandardCharsets.US_ASCII));
        if (!headOnly && body.length > 0) {
            out.write(body);
        }
        out.flush();
    }
}

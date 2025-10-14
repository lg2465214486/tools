import execjs
import random
import string


def generate_noncestr(length=8, mode="alphabet"):
    """
    生成随机字符串
    """
    if mode == "alphabet":
        charset = string.ascii_letters  # 等同于 "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    elif mode == "number":
        charset = string.digits  # 等同于 "0123456789"
    else:
        charset = string.ascii_letters  # 默认使用字母

    result = ""
    for i in range(length):
        result += random.choice(charset)

    return result


def generate_sign(args):
    js_code = """
function stringToBytes(t) {
    t = unescape(encodeURIComponent(t))
    for (var e = [], n = 0; n < t.length; n++)
        e.push(255 & t.charCodeAt(n));
    return e
}

function bytesToWords(t) {
    for (var e = [], n = 0, r = 0; n < t.length; n++,
        r += 8)
        e[r >>> 5] |= t[n] << 24 - r % 32;
    return e
}

function wordsToBytes(t) {
    for (var e = [], n = 0; n < 32 * t.length; n += 8)
        e.push(t[n >>> 5] >>> 24 - n % 32 & 255);
    return e
}

function bytesToHex(t) {
    for (var e = [], n = 0; n < t.length; n++)
        e.push((t[n] >>> 4).toString(16)),
            e.push((15 & t[n]).toString(16));
    return e.join("")
}

function a(t) {
    t = stringToBytes(t)
    var e = bytesToWords(t)
        , n = 8 * t.length
        , i = []
        , a = 1732584193
        , c = -271733879
        , s = -1732584194
        , f = 271733878
        , l = -1009589776;
    e[n >> 5] |= 128 << 24 - n % 32,
        e[(n + 64 >>> 9 << 4) + 15] = n;
    for (var p = 0; p < e.length; p += 16) {
        for (var h = a, y = c, d = s, g = f, v = l, m = 0; m < 80; m++) {
            if (m < 16)
                i[m] = e[p + m];
            else {
                var b = i[m - 3] ^ i[m - 8] ^ i[m - 14] ^ i[m - 16];
                i[m] = b << 1 | b >>> 31
            }
            var E = (a << 5 | a >>> 27) + l + (i[m] >>> 0) + (m < 20 ? (c & s | ~c & f) + 1518500249 : m < 40 ? (c ^ s ^ f) + 1859775393 : m < 60 ? (c & s | c & f | s & f) - 1894007588 : (c ^ s ^ f) - 899497514);
            l = f,
                f = s,
                s = c << 30 | c >>> 2,
                c = a,
                a = E
        }
        a += h,
            c += y,
            s += d,
            f += g,
            l += v
    }
    return bytesToHex(wordsToBytes([a, c, s, f, l]))
}
    """
    ctx = execjs.compile(js_code)
    return ctx.call("a", args)


if __name__ == '__main__':
    params = {
        "cursor": "AoJ4v/u475kDKDUyMjEyMjI1",
        "noncestr": "92434312",
        "pageSize": "10",
        "source": "1",
        "timestamp": 1760410562410,
    }
    content = ''
    for k, v in params.items():
        content += "&" + k + "=" + str(v)
    content.rstrip("&")
    print(content)
    sign = generate_sign(content)
    print(sign)


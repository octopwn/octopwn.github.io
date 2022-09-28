import os
import http.server
import socketserver
import ssl

class HttpRequestHandler(http.server.SimpleHTTPRequestHandler):
	extensions_map = {
		'': 'application/octet-stream',
		'.manifest': 'text/cache-manifest',
		'.html': 'text/html',
		'.png': 'image/png',
		'.jpg': 'image/jpg',
		'.svg':	'image/svg+xml',
		'.css':	'text/css',
		'.js':'application/x-javascript',
		'.wasm': 'application/wasm',
		'.json': 'application/json',
		'.xml': 'application/xml',
	}

def serve(ip:str, port:int = 8000, ssl_ctx = None):
	httpd = socketserver.TCPServer((ip, port), HttpRequestHandler, bind_and_activate=False)
	if ssl_ctx is not None:
		httpd.socket = ssl_ctx.wrap_socket(httpd.socket, server_side=True)
	httpd.server_bind()
	httpd.server_activate()
	
	try:
		print(f"Serving at http://{ip}:{port}")
		httpd.serve_forever()
	except KeyboardInterrupt:
		pass
	finally:
		httpd.socket.close()

def main():
	import argparse
	parser = argparse.ArgumentParser(description='Simple HTTP server')
	parser.add_argument('-a', '--address', default='127.0.0.1', help='IP/hostname to listen on')
	parser.add_argument('-p', '--port', type=int, default=8000, help='Port to listen on')
	parser.add_argument('-r', '--root', default='./', help='Base path to serve')
	parser.add_argument('--ssl-cert', help='Certificate file for SSL')
	parser.add_argument('--ssl-key',  help='Key file for SSL')
	parser.add_argument('--ssl-ca',  help='CA cert file for client cert validations')
	args = parser.parse_args()

	ssl_ctx = None
	if args.ssl_cert is not None:
		ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
		if args.ssl_key is None:
			raise Exception('TLS certificate is set but no keyfile!')
		ssl_ctx.load_cert_chain(args.ssl_cert, args.ssl_key)
		if args.ssl_ca is not None:
			ssl_ctx.load_verify_locations(args.ssl_ca)
			ssl_ctx.verify_mode = ssl.CERT_REQUIRED
		#if args.ssl_ciphers is not None:
		#	ssl_ctx.set_ciphers(args.ssl_ciphers)
		#if args.ssl_dh is not None:
		#	ssl_ctx.load_dh_params(args.ssl_dh)

	os.chdir(args.root)
	serve(args.address, args.port, ssl_ctx)

if __name__ == '__main__':
	main()

"""Python byte-transport host adapter for original urls.js; never decodes or draws."""
import base64,ssl,urllib.request,urllib.parse,urllib.error
from . import _native,undefined
def request_bytes(src,options):
    """Fetch owned HTTP bytes using original GET/header/body/auth/redirect policy.
    URL text, headers/body bytes, no canvas units; returns bytes or original HTTP Error.
    Worker I/O only, no Skia/native resources. Python opener/SSLContext correspond to
    Node Agent under approved host profile; sources urls.js:fetchURL/follow-redirects.
    """
    from ._imagery import field
    from ._text_css import truth
    options=options if truth(options) else {}
    headers=field(options,'headers',{})
    headers=dict(headers) if isinstance(headers,dict) else {}
    if not any(k.lower()=='user-agent' for k in headers):headers['User-Agent']='Skia Canvas'
    auth=field(options,'auth',undefined);parts=urllib.parse.urlsplit(src);url=src
    if parts.username is not None:
        if auth is undefined:auth=urllib.parse.unquote(parts.username)+':'+urllib.parse.unquote(parts.password or '')
        url=urllib.parse.urlunsplit(parts._replace(netloc=parts.netloc.rsplit('@',1)[-1]))
    if auth is not undefined and not any(k.lower()=='authorization' for k in headers):
        if not isinstance(auth,str):raise TypeError('The "auth" argument must be of type string')
        headers['Authorization']='Basic '+base64.b64encode(auth.encode('utf-8')).decode('ascii')
    parts=urllib.parse.urlsplit(url);path=field(options,'path',undefined);hostname=field(options,'hostname',undefined);port=field(options,'port',undefined)
    if path is not undefined:
        parsed=urllib.parse.urlsplit(path);parts=parts._replace(path=parsed.path,query=parsed.query)
    if hostname is not undefined or port is not undefined:
        host=parts.hostname if hostname is undefined else str(hostname);port=parts.port if port is undefined else port
        parts=parts._replace(netloc=host+(':'+str(port) if port is not None else ''))
    url=urllib.parse.urlunsplit(parts);body=field(options,'body',None);body=body if truth(body) else None
    if isinstance(body,str):body=body.encode('utf-8')
    elif body is not None:body=bytes(body)
    method=field(options,'method','GET');req=urllib.request.Request(url,data=body,headers=headers,method=method)
    class Redirect(urllib.request.HTTPRedirectHandler):
        """Original 307/308 method/body preservation and bounded redirect host policy."""
        max_redirections=21;max_repeats=21
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            """Return owned re-request, preserving payload only for 307/308; no native refs."""
            if code in (307,308):return urllib.request.Request(newurl,data=req.data,headers=req.headers,method=req.get_method())
            return super().redirect_request(req,fp,code,msg,headers,newurl)
    agent=field(options,'agent',undefined)
    context=agent if isinstance(agent,ssl.SSLContext) else ssl._create_unverified_context() if field(options,'rejectUnauthorized',True) is False else None
    opener=agent if isinstance(agent,urllib.request.OpenerDirector) else urllib.request.build_opener(Redirect(),urllib.request.HTTPSHandler(context=context))
    try:
        with opener.open(req) as stream:return stream.read()
    except urllib.error.HTTPError as error:
        if error.code in (301,302,303,307,308) and 'infinite loop' in str(error):raise _native.Error('Maximum number of redirects exceeded') from None
        raise _native.Error('Failed to load image from "'+src+'" (HTTP error '+str(error.code)+')') from None

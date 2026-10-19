import type { ModuleOptions, FairyStockfish } from 'ffish-fsx-es6';

export const FSX_VARIANTS = new Set(['rifle-chess', 'brotherhood', 'spell-chess', 'monster', 'cylinder']);

export async function ffishFsxModule(options: ModuleOptions = {}): Promise<FairyStockfish> {
    // Keep Emscripten's browser/Node loader intact, outside the browser bundle.
    const script = document.querySelector<HTMLScriptElement>('script[src*="/static/pychess-variants.js"]');
    const version = script ? new URL(script.src, window.location.href).search : '';
    const url = `/static/ffish-fsx.js${version}`;
    const { default: create } = await import(url) as typeof import('ffish-fsx-es6');
    return create({
        locateFile: path => `/static/${path}${version}`,
        ...options,
    });
}

// Kept in lockstep with variants-fsx.ini; never load these FSX rules into upstream.
export const fsxVariantsIni = `# Only FSX-specific definitions used by this site. Spell Chess is built in.
[rifle-chess:chess]
rifleCapture = true

[brotherhood:chess]
captureForbidden = p:p n:n r:r q:q b:b

# FSX variants.ini: White has two moves, Black one; kings are capturable.
[monster:extinction]
startFen = rnbqkbnr/pppppppp/8/8/8/8/2PPPP2/4K3 w kq - 0 1
multimoves = 2 1
extinctionPieceTypes = k
promotionPieceTypes = nbrq

# FSX variants.ini: files wrap around the board; castling is disabled.
[cylinder:chess]
startFen = rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1
cylindrical = true
castling = false
`;

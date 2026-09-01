import React from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Printer, QrCode } from 'lucide-react';

// Printable sheet of one QR code per asset. Each code encodes the bare asset_id
// string (e.g. "EXC-101") — the scanner in CheckInOutModal reads it straight back.
export default function AssetQrSheet({ assets = [] }) {
  return (
    <div className="space-y-4">
      <div className="bg-[#141414] border border-[#242424] rounded-2xl p-5 flex items-center justify-between print:hidden">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center">
            <QrCode className="w-4 h-4 mr-2 text-[#FFCD11]" />
            Asset QR Tags
          </h3>
          <p className="text-xs text-neutral-400 mt-0.5">
            One code per machine. Print and attach to the equipment, or scan on-screen with a phone.
            Each encodes the plain asset ID.
          </p>
        </div>
        <button
          onClick={() => window.print()}
          className="bg-[#FFCD11] hover:bg-[#E5B80E] text-black font-extrabold px-4 py-2 rounded-lg text-xs flex items-center cursor-pointer"
        >
          <Printer className="w-4 h-4 mr-1.5" />
          Print Sheet
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 print:grid-cols-3">
        {assets.map((a) => (
          <div
            key={a.id}
            className="bg-white rounded-xl p-4 flex flex-col items-center text-center border border-neutral-300"
          >
            <QRCodeSVG value={a.id} size={200} level="L" marginSize={4} />
            <div className="mt-3 font-mono font-black text-black text-sm">{a.id}</div>
            <div className="text-[11px] text-neutral-600">{a.name}</div>
            <div className="text-[10px] text-neutral-400">{a.type}</div>
          </div>
        ))}
      </div>

      {assets.length === 0 && (
        <p className="text-xs text-neutral-500">No assets loaded yet.</p>
      )}
    </div>
  );
}

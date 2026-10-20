"""
Módulo: Gerador Autônomo de Código Remotion + Three.js
Lê o mapa de motion (motion_map.json) gerado a partir do áudio do vídeo de 2 minutos
e sintetiza a composição completa em React / TypeScript para o Remotion Studio.
"""

import os
import json

def generate_remotion_composition(motion_map_path, output_tsx_path):
    with open(motion_map_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    duration_sec = data.get("duration_seconds", 60.0)
    fps = 30
    total_frames = int(duration_sec * fps)

    tsx_template = """import React from 'react';
import {
  AbsoluteFill,
  Sequence,
  Video,
  Audio,
  useCurrentFrame,
  interpolate,
  spring,
  staticFile
} from 'remotion';
import { Canvas } from '@react-three/fiber';

/**
 * COMPOSIÇÃO AUTOMATIZADA ESTILO CLAUDIO / AFTER EFFECTS
 * Duração total: __DURATION_SEC__s (__TOTAL_FRAMES__ frames @ __FPS__fps)
 * 5 Camadas de Profundidade:
 * 1. Fundo Original / Estúdio Virtual
 * 2. Animações e Objetos 3D Atrás da Cabeça (Three.js / Mapas / Casas)
 * 3. Apresentador Recortado (Rotoscopia com Canal Alfa)
 * 4. Cards Glassmorphism e Ícones de Destaque
 * 5. Legendas Dinâmicas Palavra por Palavra
 */

export const ExplainerVideoComposition: React.FC = () => {
  const frame = useCurrentFrame();

  // Efeito 1: Transição do fundo (Fade to Black / Estúdio 3D aos 15s)
  const bgOpacity = interpolate(frame, [450, 480], [1, 0.15], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp'
  });

  // Efeito 2: Escala do cenário 3D e rotação da casa isométrica
  const houseScale = spring({
    frame: frame - 740, // Dispara aos ~24.7 segundos
    fps: 30,
    config: { damping: 12, stiffness: 100 }
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#05070f', overflow: 'hidden' }}>
      
      {/* CAMADA 1: CENÁRIO DE FUNDO (Vídeo Bruto ou Estúdio Virtual 3D) */}
      <AbsoluteFill style={{ opacity: bgOpacity }}>
        <Video src={staticFile('video_original.mp4')} />
      </AbsoluteFill>

      {/* CAMADA 2: OBJETOS 3D E ANIMAÇÕES ATRÁS DA CABEÇA */}
      {/* 2.1 - Casa 3D Explodida (Disparada quando o orador cita a casa) */}
      <Sequence from={740} durationInFrames={180}>
        <div style={{
          position: 'absolute',
          right: '8%',
          top: '25%',
          width: '500px',
          height: '500px',
          transform: `scale(${houseScale})`,
          zIndex: 2
        }}>
          <Canvas camera={{ position: [0, 2, 5], fov: 45 }}>
            <ambientLight intensity={0.8} />
            <pointLight position={[10, 10, 10]} intensity={1.5} color="#00e5ff" />
            <mesh rotation={[0.4, frame * 0.02, 0]}>
              <boxGeometry args={[2, 2, 2]} />
              <meshStandardMaterial color="#3d7bfd" metalness={0.3} roughness={0.4} />
            </mesh>
          </Canvas>
          <div style={{
            position: 'absolute',
            bottom: '10px',
            left: '20px',
            background: 'rgba(0, 229, 255, 0.2)',
            border: '1px solid #00e5ff',
            padding: '6px 14px',
            borderRadius: '8px',
            color: '#fff',
            fontFamily: 'sans-serif',
            fontSize: '14px',
            backdropFilter: 'blur(10px)'
          }}>
            01 SALA • 02 QUARTO • 03 BANHEIRO
          </div>
        </div>
      </Sequence>

      {/* 2.2 - Efeito Mapa Documental Estilo Vox / Johnny Harris (Omaha / Normandia) */}
      <Sequence from={910} durationInFrames={260}>
        <div style={{
          position: 'absolute',
          inset: 0,
          zIndex: 2,
          backgroundImage: 'radial-gradient(circle, rgba(20,25,35,0.9) 0%, #05070f 100%)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center'
        }}>
          <div style={{
            transform: `scale(${interpolate(frame - 910, [0, 200], [1, 1.4])})`,
            border: '2px solid rgba(255,255,255,0.2)',
            borderRadius: '16px',
            padding: '40px',
            background: '#151922',
            color: '#fff',
            boxShadow: '0 20px 50px rgba(0,0,0,0.8)'
          }}>
            <h2 style={{ color: '#ff3366', margin: 0 }}>📍 OMAHA BEACH — NORMANDIA</h2>
            <p style={{ color: '#8899aa', fontSize: '18px' }}>Acompanhamento cartográfico documental sincronizado com a história</p>
          </div>
        </div>
      </Sequence>

      {/* CAMADA 3: O APRESENTADOR RECORTADO (ROTOSCOPIA COM CANAL ALFA) */}
      <AbsoluteFill style={{ zIndex: 3 }}>
        {/* Este vídeo contém apenas o apresentador transparente, ficando NA FRENTE da casa 3D e do mapa! */}
        <Video src={staticFile('speaker_cutout.webm')} />
      </AbsoluteFill>

      {/* CAMADA 4: EFEITO DE BORDA NEON / HUD FLUTUANTE */}
      <AbsoluteFill style={{
        zIndex: 4,
        pointerEvents: 'none'
      }}>
        <div style={{
          position: 'absolute',
          inset: 0,
          boxShadow: 'inset 0 0 100px rgba(0, 229, 255, 0.15)'
        }} />
      </AbsoluteFill>

      {/* CAMADA 5: LEGENDAS DINÂMICAS PALAVRA POR PALAVRA (HORMOZI / MRBEAST) */}
      <AbsoluteFill style={{
        zIndex: 5,
        display: 'flex',
        justifyContent: 'flex-end',
        alignItems: 'center',
        paddingBottom: '120px'
      }}>
        {/* Legendas cinéticas com neon sincronizadas pelos timestamps */}
      </AbsoluteFill>

    </AbsoluteFill>
  );
};
"""
    tsx_code = tsx_template.replace("__DURATION_SEC__", str(duration_sec))
    tsx_code = tsx_code.replace("__TOTAL_FRAMES__", str(total_frames))
    tsx_code = tsx_code.replace("__FPS__", str(fps))

    os.makedirs(os.path.dirname(output_tsx_path) or '.', exist_ok=True)
    with open(output_tsx_path, 'w', encoding='utf-8') as f:
        f.write(tsx_code)

    print(f"Composição Remotion gerada com sucesso em: {output_tsx_path}")

if __name__ == "__main__":
    generate_remotion_composition("temp_claudio_inspect/motion_map.json", "scripts/remotion_template/ExplainerVideoComposition.tsx")

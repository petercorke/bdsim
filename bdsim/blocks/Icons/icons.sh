#! /bin/bash

bdtex2icon -r 300 -o sum.png -t '\sum'
bdtex2icon -r 450 -o prod.png -t '\Pi'
bdtex2icon -r 200 -o norm.png -t '\| \cdot \|'
bdtex2icon -r 250 -o det.png -t '| \cdot |'
bdtex2icon -r 110 -o cond.png -t '\mathrm{cond}(\cdot)'
bdtex2icon -r 150 -o fkine.png -t '\vec{T}\!\left(\mat{q}\right)'
bdtex2icon -r 150 -o ikine.png -t '\mat{q}\!\left(\vec{T}\right)'
bdtex2icon -r 150 -o jacobian.png -t '\mat{J}\!\left(\vec{q}\right)'
bdtex2icon -r 300 -o time.png -t 't'
bdtex2icon -r 100 -o point2tr.png -t '\begin{array}{c|c} \mat{1} & \vec{t}\\ \hline 0 & 1 \end{array}'
bdtex2icon -r 120 -o tr2delta.png -t '\vec{\Delta}\!\left(\mat{T}\right)'
bdtex2icon -r 120 -o delta2tr.png -t '\mat{T}\!\left(\vec{\Delta}\right)'

bdtex2icon -r 140 -o dposeintegrator.png -t '\sum_0^T \vec{\nu}'

bdtex2icon -r 150 -o dict.png -t '\mathbf{\{\cdots\}}'
bdtex2icon -r 150 -o index.png -t '\mathbf{[}k\mathrm{]}'
bdtex2icon -r 150 -o item.png -t '\mathbf{\{\}[}k\mathrm{]}'

bdtex2icon -r 180 -o transpose.png -t '\mat{A}^{\!T}'
bdtex2icon -r 180 -o inverse.png -t '\mat{A}^{\!-\!1}'

bdtex2icon -r 250 -o integrator.png -t '\frac{1}{s}'
bdtex2icon -r 220 -o dintegrator.png -t '\frac{z}{z-1}'

bdtex2icon -r 150 -o lti_siso.png -t '\frac{N(s)}{D(s)}'
bdtex2icon -r 90 -o lti_ss.png -t '\begin{array}{c|c} A & B\\ \hline C & D \end{array}'

bdtex2icon -r 90 -o tr2t.png -t '\begin{array}{c|c} \mat{R} & \vec{t}\\ \hline 0 & 1 \end{array}'

bdtex2icon -r 100 -o gravload.png -t '\vec{g}\!\left(\vec{q}\right)'
bdtex2icon -r 100 -o coriolis.png -t '\mat{C}\left(\vec{q}, \dvec{q}\right)'
bdtex2icon -r 100 -o inertia.png -t '\mat{M}\!\left(\vec{q}\right)'

bdtex2icon -r 100 -o fdyn.png -t '\ddvec{q}\left(\vec{q}, \vec{\tau}\right)'
bdtex2icon -r 100 -o fdynx.png -t '\ddvec{x}\left(\vec{q}, \vec{w}\right)'

bdtex2icon -r 80 -o idyn.png -t '\vec{\tau}\!\left(\vec{q}, \dvec{q}, \ddvec{q}\right)'
bdtex2icon -r 80 -o idynx.png -t '\vec{w}\!\left(\vec{q}, \dvec{q}, \ddvec{x}\right)'

bdtex2icon -r 180 -o pose_postmul.png -t '\mathbf{\oplus\\!\pose[x]_y}'
bdtex2icon -r 180 -o pose_premul.png -t '\mathbf{\pose[x]_y\\!\oplus}'
bdtex2icon -r 170 -o pose_inverse.png -t '\mathbf{\ominus}'
bdtex2icon -r 150 -o transform_vector.png -t '\mathbf{\pose[x]_y}\\!\sbullet\\!\vec{p}'
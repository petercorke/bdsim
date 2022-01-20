#! /bin/bash

./tex2icon.py -r 300 -o sum.png -t '\sum'
./tex2icon.py -r 450 -o prod.png -t '\Pi'
./tex2icon.py -r 200 -o norm.png -t '\| \cdot \|'
./tex2icon.py -r 250 -o det.png -t '| \cdot |'
./tex2icon.py -r 110 -o cond.png -t '\mathrm{cond}(\cdot)'
./tex2icon.py -r 150 -o fkine.png -t '\vec{T}\!\left(\mat{q}\right)'
./tex2icon.py -r 150 -o ikine.png -t '\mat{q}\!\left(\vec{T}\right)'
./tex2icon.py -r 150 -o jacobian.png -t '\mat{J}\!\left(\vec{q}\right)'
./tex2icon.py -r 300 -o time.png -t 't'
./tex2icon.py -r 100 -o point2tr.png -t '\begin{array}{c|c} \mat{1} & \vec{t}\\ \hline 0 & 1 \end{array}'
./tex2icon.py -r 120 -o tr2delta.png -t '\vec{\Delta}\!\left(\mat{T}\right)'
./tex2icon.py -r 120 -o delta2tr.png -t '\mat{T}\!\left(\vec{\Delta}\right)'

./tex2icon.py -r 140 -o dposeintegrator.png -t '\sum_0^T \vec{\nu}'

./tex2icon.py -r 150 -o dict.png -t '\mathbf{\{\cdots\}}'
./tex2icon.py -r 150 -o index.png -t '\mathbf{[}k\mathrm{]}'
./tex2icon.py -r 150 -o item.png -t '\mathbf{\{\}[}k\mathrm{]}'

./tex2icon.py -r 180 -o transpose.png -t '\mat{A}^{\!T}'
./tex2icon.py -r 180 -o inverse.png -t '\mat{A}^{\!-\!1}'

./tex2icon.py -r 250 -o integrator.png -t '\frac{1}{s}'
./tex2icon.py -r 250 -o dintegrator.png -t '\frac{1}{z}'

./tex2icon.py -r 150 -o lti_siso.png -t '\frac{N(s)}{D(s)}'
./tex2icon.py -r 90 -o lti_ss.png -t '\begin{array}{c|c} A & B\\ \hline C & D \end{array}'

./tex2icon.py -r 90 -o tr2t.png -t '\begin{array}{c|c} \mat{R} & \vec{t}\\ \hline 0 & 1 \end{array}'

./tex2icon.py -r 100 -o gravload.png -t '\vec{g}\!\left(\vec{q}\right)'
./tex2icon.py -r 100 -o coriolis.png -t '\mat{C}\left(\vec{q}, \dvec{q}\right)'
./tex2icon.py -r 100 -o inertia.png -t '\mat{M}\!\left(\vec{q}\right)'

./tex2icon.py -r 100 -o fdyn.png -t '\ddvec{q}\left(\vec{q}, \vec{\tau}\right)'
./tex2icon.py -r 100 -o fdynx.png -t '\ddvec{x}\left(\vec{q}, \vec{w}\right)'

./tex2icon.py -r 80 -o idyn.png -t '\vec{\tau}\!\left(\vec{q}, \dvec{q}, \ddvec{q}\right)'
./tex2icon.py -r 80 -o idynx.png -t '\vec{w}\!\left(\vec{q}, \dvec{q}, \ddvec{x}\right)'

./tex2icon.py -r 180 -o pose_postmul.png -t '\mathbf{\oplus\\!\pose[x]_y}'
./tex2icon.py -r 180 -o pose_premul.png -t '\mathbf{\pose[x]_y\\!\oplus}'
./tex2icon.py -r 170 -o pose_inverse.png -t '\mathbf{\ominus}'
./tex2icon.py -r 150 -o transform_vector.png -t '\mathbf{\pose[x]_y}\\!\sbullet\\!\vec{p}'
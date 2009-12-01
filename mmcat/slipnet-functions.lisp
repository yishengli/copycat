;---------------------------------------------
; slipnode.activate-from-workspace | REMOVED
; slipnode.add-activation-to-buffer
; slipnode.subtract-activation-from-buffer
;---------------------------------------------

;---------------------------------------------
; slipnode.decay | Slipnode.decay
;---------------------------------------------

(defun update-slipnet (&aux amount-to-spread full-activation-probability)

; Decay and spread activation (change buffers, not actual activation, until
; all nodes have been updated).
  (loop for node in *slipnet* do

        (send node :decay)

	; If node is active, spread activation to neighbors.
        ; Note that activation spreading uses the intrinsic link-length,
        ; not the shrunk link length.
	(if* (= (send node :activation) %max-activation%)
         then  ; Give each neighbor the percentage of the activation
               ; proportional to the inverse of its distance from the 
	       ; original node.
	       (loop for link in (send node :outgoing-links) do
                    (setq amount-to-spread 
			  (round (* (/ (send link 
					     :intrinsic-degree-of-association)
				        100.0)
			            (send node :activation))))
		    (send (send link :to-node) 
			  :add-activation-to-buffer amount-to-spread))))
		    
  ; Next, the actual activation of each node is updated for the next time step.
  (loop for node in *slipnet* do
        (send node :set-activation 
	           (min %max-activation% 
			(+ (send node :activation) 
			   (send node :activation-buffer))))

        ; If node is still clamped, then activate it.
	(if* (send node :clamp)
	 then (send node :set-activation %max-activation%)

	 else ; See if node should become active.  The decision is
	      ; is a probabilistic function of activation.
              (if* (>= (send node :activation) %full-activation-threshold%)
	       then (setq full-activation-probability
			  (cube (/ (send node :activation) 100)))
                    (if* (eq (flip-coin full-activation-probability) 'heads)
	             then (send node :set-activation %max-activation%))))

        (send node :set-activation-buffer 0)))


;---------------------------------------------
; get-top-down-codelets | Slipnet.top_down_codelets
;---------------------------------------------

(defun get-top-down-codelets ()
; Returns a list of top-down codelets, attached to active nodes, to be posted.
  (loop for node in *slipnet* do
        (if* (and (>= (send node :activation) %full-activation-threshold%)
		  (send node :codelets))
	 then (send node :get-codelets))))
  
;---------------------------------------------

(defmethod (slipnode :get-codelets) ()
  (loop for codelet in codelets do 
        ; Decide whether or not to post this codelet, and if so, how many
	; copies to post.
        (if* (eq (flip-coin (get-post-codelet-probability 
				(send codelet :structure-category))) 'heads)
         then (loop for i from 1 to (get-num-of-codelets-to-post
					(send codelet :structure-category)) do
                    (push (make-codelet (send codelet :codelet-type)
			                (send codelet :arguments)
                                        (get-urgency-bin 
                                                (* (send self :activation)
						   (/ (send self :conceptual-depth) 
						      100))))
                           *codelets-to-post*)))))
						   
;---------------------------------------------
